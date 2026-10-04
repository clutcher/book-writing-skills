#!/usr/bin/env python3
"""Find names in the metadata of the images a paper uses, before an anonymous paper goes out.

An image file can carry who made it: the Author of a PDF (its Info dictionary or its XMP
packet), the Artist, Copyright or XPAuthor of a JPEG or PNG (EXIF, PNG text chunks, XMP),
the %%For line of an EPS. LaTeX copies a JPEG into the PDF as it is, with all of that, and
pdflatex also copies the Info dictionary of an included PDF unless \\pdfsuppressptexinfo is
set. So an anonymous paper is only anonymous when its images are.

Each image is reported (finding class image-metadata, a defect) when a name field holds any
text, or when a tool field (Creator, Producer, Software, Title, Comment and the like) holds an
email address or the path of a home folder (on Linux, macOS or Windows). The check reads
the files only; it never changes them. Clean an image by saving it again without its
metadata (for example `exiftool -all= image.jpg`), then build again.

Give image files or folders (folders are searched for .pdf, .png, .jpg, .jpeg and .eps).
build-book.sh runs it on the build folder of an anonymous paper, and arxiv-bundle-check.py
uses the same reader on an anonymous bundle.
"""

import argparse
import binascii
import re
import struct
import sys
import tempfile
import zlib
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

from check_output import DEFECT, CheckReport, add_output_arguments, run_main, tool_failed

TOOL = "image_metadata"
CLASSES = {"image-metadata": DEFECT}
IMAGE_ENDINGS = (".pdf", ".png", ".jpg", ".jpeg", ".eps")
READ_LIMIT = 200 * 1024 * 1024
STREAM_OUTPUT_LIMIT = 16 * 1024 * 1024
STREAM_TOTAL_LIMIT = 128 * 1024 * 1024

PDF_NAME_KEYS = ("Author",)
PDF_TOOL_KEYS = ("Creator", "Producer", "Title")
PDF_ENTRY = re.compile(rb"/(" + b"|".join(key.encode() for key in PDF_NAME_KEYS + PDF_TOOL_KEYS)
                       + rb")\s*(\(|<(?!<))")
STREAM_START = re.compile(rb"stream\r?\n")

TIFF_NAME_TAGS = {0x013B: "Artist", 0x8298: "Copyright", 0x9C9D: "XPAuthor"}
TIFF_TOOL_TAGS = {0x0131: "Software", 0x010E: "ImageDescription", 0x9C9B: "XPTitle",
                  0x9C9C: "XPComment"}
TIFF_UTF16_TAGS = {0x9C9B, 0x9C9C, 0x9C9D}
TIFF_TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8}

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_NAME_KEYS = ("Author", "Artist", "Copyright")
PNG_XMP_KEY = "XML:com.adobe.xmp"

JPEG_EXIF_START = b"Exif\x00\x00"
JPEG_XMP_START = b"http://ns.adobe.com/xap/1.0/\x00"

EPS_NAME_LINES = ("For",)
EPS_TOOL_LINES = ("Creator", "Title")

XMP_NAME_PROPERTIES = ("dc:creator", "pdf:Author", "photoshop:Credit", "xmpRights:Owner",
                       "dc:rights")
XMP_TOOL_PROPERTIES = ("xmp:CreatorTool", "pdf:Producer", "dc:title", "dc:description")
XMP_LIST_ITEM = re.compile(r"<rdf:li\b[^>]*>(.*?)</rdf:li>", re.S)
XML_TAG = re.compile(r"<[^>]+>")

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
HOME_FOLDER_ROOTS = ("home", "Users")
HOME_FOLDER = re.compile(r"(?:/(?:" + "|".join(HOME_FOLDER_ROOTS) + r")/|[A-Za-z]:[\\/]+Users[\\/]+)"
                         r"[^/\\\s]+", re.I)


def leaks_a_name(value):
    return bool(EMAIL.search(value) or HOME_FOLDER.search(value))


def finding(field, value, is_name_field):
    value = " ".join(value.replace("\x00", " ").split())
    if not value:
        return None
    if is_name_field or leaks_a_name(value):
        return (field, value)
    return None


def text_of(data):
    if data.startswith(b"\xfe\xff"):
        return data[2:].decode("utf-16-be", errors="replace")
    if data.startswith(b"\xff\xfe"):
        return data[2:].decode("utf-16-le", errors="replace")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


PDF_ESCAPES = {ord("n"): b"\n", ord("r"): b"\r", ord("t"): b"\t", ord("b"): b"\b",
               ord("f"): b"\f", ord("("): b"(", ord(")"): b")", ord("\\"): b"\\"}


def pdf_literal_string(data, at):
    result = bytearray()
    depth = 1
    position = at
    while position < len(data) and depth:
        byte = data[position]
        if byte == ord("\\") and position + 1 < len(data):
            following = data[position + 1]
            if following in PDF_ESCAPES:
                result += PDF_ESCAPES[following]
                position += 2
            elif ord("0") <= following <= ord("7"):
                digits = re.match(rb"[0-7]{1,3}", data[position + 1:position + 4]).group(0)
                result.append(int(digits, 8) & 0xFF)
                position += 1 + len(digits)
            else:
                position += 2
            continue
        if byte == ord("("):
            depth += 1
        elif byte == ord(")"):
            depth -= 1
            if depth == 0:
                break
        result.append(byte)
        position += 1
    return bytes(result)


def pdf_hex_string(data, at):
    end = data.find(b">", at)
    digits = re.sub(rb"\s", b"", data[at:end if end >= 0 else len(data)])
    if len(digits) % 2:
        digits += b"0"
    try:
        return binascii.unhexlify(digits)
    except binascii.Error:
        return b""


def pdf_texts(data):
    texts = [data]
    budget = STREAM_TOTAL_LIMIT
    for match in STREAM_START.finditer(data):
        if budget <= 0:
            break
        try:
            inflated = zlib.decompressobj().decompress(data[match.end():],
                                                       min(budget, STREAM_OUTPUT_LIMIT))
        except zlib.error:
            continue
        budget -= len(inflated)
        texts.append(inflated)
    return texts


def pdf_fields(data):
    found = []
    for text in pdf_texts(data):
        for match in PDF_ENTRY.finditer(text):
            key = match.group(1).decode()
            start = match.end()
            raw = (pdf_literal_string(text, start) if match.group(2) == b"("
                   else pdf_hex_string(text, start))
            found.append(finding(f"PDF {key}", text_of(raw), key in PDF_NAME_KEYS))
        found.extend(xmp_fields(text.decode("utf-8", errors="replace")))
    return found


def xmp_values(xmp, name):
    values = []
    element = re.compile(rf"<{re.escape(name)}\b[^>]*?(?:/>|>(.*?)</{re.escape(name)}>)", re.S)
    for match in element.finditer(xmp):
        inner = match.group(1) or ""
        items = XMP_LIST_ITEM.findall(inner)
        values.extend(items if items else [inner])
    attribute = re.compile(rf"\b{re.escape(name)}=\"([^\"]*)\"")
    values.extend(attribute.findall(xmp))
    return [XML_TAG.sub(" ", value) for value in values]


def xmp_fields(text):
    if "<x:xmpmeta" not in text and "<rdf:RDF" not in text:
        return []
    found = []
    for name in XMP_NAME_PROPERTIES + XMP_TOOL_PROPERTIES:
        for value in xmp_values(text, name):
            found.append(finding(f"XMP {name}", value, name in XMP_NAME_PROPERTIES))
    return found


def tiff_fields(tiff):
    if len(tiff) < 8 or tiff[:2] not in (b"II", b"MM"):
        return []
    order = "<" if tiff[:2] == b"II" else ">"
    (first_folder,) = struct.unpack_from(order + "I", tiff, 4)
    if first_folder + 2 > len(tiff):
        return []
    (count,) = struct.unpack_from(order + "H", tiff, first_folder)
    found = []
    for index in range(count):
        at = first_folder + 2 + index * 12
        if at + 12 > len(tiff):
            break
        tag, kind, number = struct.unpack_from(order + "HHI", tiff, at)
        if tag not in TIFF_NAME_TAGS and tag not in TIFF_TOOL_TAGS:
            continue
        size = TIFF_TYPE_SIZES.get(kind, 1) * number
        value_at = at + 8 if size <= 4 else struct.unpack_from(order + "I", tiff, at + 8)[0]
        raw = tiff[value_at:value_at + size]
        value = (raw.decode("utf-16-le", errors="replace") if tag in TIFF_UTF16_TAGS
                 else raw.decode("utf-8", errors="replace"))
        field = TIFF_NAME_TAGS.get(tag) or TIFF_TOOL_TAGS[tag]
        found.append(finding(f"EXIF {field}", value, tag in TIFF_NAME_TAGS))
    return found


def jpeg_fields(data):
    found = []
    position = 2
    while position + 4 <= len(data) and data[position] == 0xFF:
        marker = data[position + 1]
        if marker == 0xFF:
            position += 1
            continue
        if marker in (0x01, *range(0xD0, 0xD9)):
            position += 2
            continue
        if marker in (0xD9, 0xDA):
            break
        (length,) = struct.unpack_from(">H", data, position + 2)
        segment = data[position + 4:position + 2 + length]
        if marker == 0xE1 and segment.startswith(JPEG_EXIF_START):
            found.extend(tiff_fields(segment[len(JPEG_EXIF_START):]))
        elif marker == 0xE1 and segment.startswith(JPEG_XMP_START):
            found.extend(xmp_fields(segment[len(JPEG_XMP_START):].decode("utf-8", "replace")))
        elif marker == 0xFE:
            found.append(finding("JPEG comment", text_of(segment), False))
        position += 2 + length
    return found


def png_text_chunk(kind, body):
    key, _, rest = body.partition(b"\x00")
    key = key.decode("latin-1")
    if kind == b"tEXt":
        return key, rest.decode("latin-1")
    if kind == b"zTXt":
        return key, zlib.decompress(rest[1:]).decode("latin-1", errors="replace")
    compressed = rest[:1] == b"\x01"
    _, _, rest = rest[2:].partition(b"\x00")
    _, _, text = rest.partition(b"\x00")
    if compressed:
        text = zlib.decompress(text)
    return key, text.decode("utf-8", errors="replace")


def png_fields(data):
    found = []
    position = len(PNG_SIGNATURE)
    while position + 8 <= len(data):
        length, kind = struct.unpack_from(">I4s", data, position)
        body = data[position + 8:position + 8 + length]
        position += 12 + length
        if kind == b"eXIf":
            found.extend(tiff_fields(body))
        elif kind in (b"tEXt", b"zTXt", b"iTXt"):
            try:
                key, value = png_text_chunk(kind, body)
            except zlib.error:
                continue
            if key == PNG_XMP_KEY:
                found.extend(xmp_fields(value))
            else:
                found.append(finding(f"PNG {key}", value, key in PNG_NAME_KEYS))
        elif kind == b"IEND":
            break
    return found


def eps_fields(data):
    text = data.decode("latin-1")
    found = []
    for line in text.splitlines():
        match = re.match(r"%%(\w+):\s*(.*)", line)
        if not match:
            continue
        key, value = match.groups()
        if key in EPS_NAME_LINES or key in EPS_TOOL_LINES:
            found.append(finding(f"EPS %%{key}", value.strip("() "), key in EPS_NAME_LINES))
        if key == "EndComments":
            break
    found.extend(xmp_fields(text))
    return found


def name_fields(path):
    with open(path, "rb") as opened:
        data = opened.read(READ_LIMIT)
    if data.startswith(PNG_SIGNATURE):
        found = png_fields(data)
    elif data.startswith(b"\xff\xd8"):
        found = jpeg_fields(data)
    elif data.startswith(b"%PDF"):
        found = pdf_fields(data)
    elif data.startswith(b"%!PS") or data.startswith(b"\xc5\xd0\xd3\xc6"):
        found = eps_fields(data)
    else:
        found = []
    unique = []
    for item in found:
        if item and item not in unique:
            unique.append(item)
    return unique


def add_findings(report, shown_name, path):
    for field, value in name_fields(path):
        report.add(shown_name, "image-metadata",
                   f"{field} holds \"{value}\"; an anonymous paper must not carry a name in an "
                   f"image file. Save the image again without its metadata "
                   f"(for example exiftool -all=), then build again")


def image_files(paths):
    files = []
    for given in paths:
        given = Path(given)
        if given.is_dir():
            files.extend(sorted((path, str(path.relative_to(given)))
                                for path in given.rglob("*")
                                if path.is_file() and path.suffix.lower() in IMAGE_ENDINGS))
        else:
            files.append((given, str(given)))
    return files


SAMPLE_HOME_PATH = "/".join(("", HOME_FOLDER_ROOTS[0], "jsecret", "plots", "watering"))


def sample_files(folder):
    folder = Path(folder)
    exif = (b"MM\x00\x2a\x00\x00\x00\x08\x00\x02"
            b"\x01\x3b\x00\x02\x00\x00\x00\x0c\x00\x00\x00\x26"
            b"\x01\x31\x00\x02\x00\x00\x00\x04Gimp"
            b"\x00\x00\x00\x00Jane Secret\x00")
    jpeg = (b"\xff\xd8\xff\xe1" + struct.pack(">H", len(exif) + 8) + JPEG_EXIF_START + exif
            + b"\xff\xd9")
    (folder / "photo.jpg").write_bytes(jpeg)

    def png_chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + b"\x00\x00\x00\x00"

    (folder / "plot.png").write_bytes(
        PNG_SIGNATURE + png_chunk(b"tEXt", b"Software\x00matplotlib 3.9")
        + png_chunk(b"iTXt", b"Author\x00\x00\x00\x00\x00Jane Secret")
        + png_chunk(b"tEXt", b"Source\x00" + SAMPLE_HOME_PATH.encode())
        + png_chunk(b"IEND", b""))
    (folder / "clean.png").write_bytes(
        PNG_SIGNATURE + png_chunk(b"tEXt", b"Software\x00matplotlib 3.9") + png_chunk(b"IEND", b""))
    stream = zlib.compress(b"<< /Producer (pdfTeX-1.40.28) "
                           b"/Author <feff004a0061006e00650020005300650063007200650074> >>")
    (folder / "figure.pdf").write_bytes(
        b"%PDF-1.5\n1 0 obj\n<< /Type /ObjStm >>\nstream\n" + stream
        + b"\nendstream\nendobj\n2 0 obj\n<< /Creator (Inkscape 1.3 \\(https://inkscape.org\\)) "
          b"/Title (jane.secret@example.org) >>\nendobj\n%%EOF\n")
    (folder / "chart.pdf").write_bytes(
        b"%PDF-1.4\n1 0 obj\n<< /Creator (Matplotlib v3.9) /Producer (Matplotlib pdf backend) "
        b">>\nendobj\n%%EOF\n")
    (folder / "diagram.eps").write_bytes(
        b"%!PS-Adobe-3.0 EPSF-3.0\n%%Creator: dot 12\n%%For: jsecret\n%%EndComments\n")
    (folder / "drawing.png").write_bytes(
        PNG_SIGNATURE + png_chunk(b"iTXt", b"XML:com.adobe.xmp\x00\x00\x00\x00\x00"
                                           b"<x:xmpmeta><rdf:RDF><dc:creator><rdf:Seq>"
                                           b"<rdf:li>Jane Secret</rdf:li></rdf:Seq></dc:creator>"
                                           b"<xmp:CreatorTool>Krita</xmp:CreatorTool>"
                                           b"</rdf:RDF></x:xmpmeta>") + png_chunk(b"IEND", b""))


def self_test():
    checks = []
    with tempfile.TemporaryDirectory() as scratch:
        sample_files(scratch)
        found = {name: name_fields(Path(scratch) / name)
                 for name in ("photo.jpg", "plot.png", "clean.png", "figure.pdf", "chart.pdf",
                              "diagram.eps", "drawing.png")}
        checks.append(("the EXIF Artist of a JPEG is found and its Software is not",
                       found["photo.jpg"], [("EXIF Artist", "Jane Secret")]))
        checks.append(("a PNG text Author and a home folder in its Source are found",
                       found["plot.png"], [("PNG Author", "Jane Secret"),
                                           ("PNG Source", SAMPLE_HOME_PATH)]))
        checks.append(("a PNG with only its tool name is clean", found["clean.png"], []))
        checks.append(("a UTF-16 Author in a compressed PDF stream and an email Title are found",
                       found["figure.pdf"], [("PDF Title", "jane.secret@example.org"),
                                             ("PDF Author", "Jane Secret")]))
        checks.append(("a PDF that names only its tools is clean", found["chart.pdf"], []))
        checks.append(("the %%For line of an EPS is found", found["diagram.eps"],
                       [("EPS %%For", "jsecret")]))
        checks.append(("the XMP creator of a PNG is found", found["drawing.png"],
                       [("XMP dc:creator", "Jane Secret")]))
        report = CheckReport(TOOL, CLASSES)
        for path, shown in image_files([scratch]):
            add_findings(report, shown, path)
        checks.append(("a folder is searched and each finding is a defect",
                       (sorted({key for key, _, _ in report.items}), report.exit_code()),
                       (["diagram.eps", "drawing.png", "figure.pdf", "photo.jpg", "plot.png"],
                        1)))
    failures = [(name, got, expected) for name, got, expected in checks if got != expected]
    for name, got, expected in failures:
        print(f"FAIL  {name}: got {got!r}, expected {expected!r}")
    print(f"image_metadata self-test: {len(checks) - len(failures)}/{len(checks)} passed")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="exit codes: 0 no names found, 1 an image holds a "
                                            "name, 2 the tool failed")
    add_output_arguments(parser)
    parser.add_argument("paths", nargs="*", help="image files or folders to read")
    parser.add_argument("--self-test", action="store_true",
                        help="run the built-in tests with small made-up image files")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if not args.paths:
        return tool_failed("name at least one image file or folder", TOOL)
    missing = [path for path in args.paths if not Path(path).exists()]
    if missing:
        return tool_failed(f"no such file or folder: {', '.join(missing)}", TOOL)
    report = CheckReport(TOOL, CLASSES)
    for path, shown in image_files(args.paths):
        add_findings(report, shown, path)
    return report.emit(args.format)


if __name__ == "__main__":
    run_main(main, TOOL)
