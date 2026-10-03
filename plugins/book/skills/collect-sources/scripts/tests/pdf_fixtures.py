import struct
import subprocess
import tempfile
from pathlib import Path

PAGE_WIDTH = 612
PAGE_HEIGHT = 792
LINES_PER_PAGE = 48


def escaped(line):
    return line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def text_page_stream(lines):
    body = ["BT", "/F1 11 Tf", "14 TL", "56 740 Td"]
    body += ["(%s) Tj T*" % escaped(line) for line in lines]
    body.append("ET")
    return "\n".join(body).encode("latin-1")


def image_page_stream():
    return ("q %d 0 0 %d 0 0 cm /Im1 Do Q" % (PAGE_WIDTH, PAGE_HEIGHT)).encode("ascii")


def stream_object(dictionary, data):
    return b"<< " + dictionary + b" /Length %d >>\nstream\n" % len(data) + data + b"\nendstream"


def assemble(objects):
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1, xref)
    return bytes(out)


def pages_of(lines):
    return [lines[start:start + LINES_PER_PAGE] for start in range(0, len(lines), LINES_PER_PAGE)]


def write_text_pdf(path, lines):
    pages = pages_of(lines)
    first_page = 4
    kids = " ".join("%d 0 R" % (first_page + 2 * index) for index in range(len(pages)))
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        ("<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(pages))).encode("ascii"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for index, page in enumerate(pages):
        content = first_page + 2 * index + 1
        objects.append(("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Resources "
                        "<< /Font << /F1 3 0 R >> >> /Contents %d 0 R >>"
                        % (PAGE_WIDTH, PAGE_HEIGHT, content)).encode("ascii"))
        objects.append(stream_object(b"", text_page_stream(page)))
    Path(path).write_bytes(assemble(objects))


def png_parts(png):
    position, width, height, colors, data = 8, 0, 0, 1, bytearray()
    while position < len(png):
        length, kind = struct.unpack(">I4s", png[position:position + 8])
        chunk = png[position + 8:position + 8 + length]
        if kind == b"IHDR":
            width, height = struct.unpack(">II", chunk[:8])
            colors = 3 if chunk[9] == 2 else 1
        elif kind == b"IDAT":
            data += chunk
        position += 12 + length
    return width, height, colors, bytes(data)


def write_scanned_pdf(path, lines):
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / "source.pdf"
        write_text_pdf(source, lines)
        subprocess.run(["pdftoppm", "-r", "200", "-gray", "-png", str(source),
                        str(Path(folder) / "page")], check=True, capture_output=True)
        images = [png_parts((Path(folder) / name).read_bytes())
                  for name in sorted(p.name for p in Path(folder).glob("page*.png"))]
    kids = " ".join("%d 0 R" % (3 + 3 * index) for index in range(len(images)))
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        ("<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(images))).encode("ascii"),
    ]
    for index, (width, height, colors, data) in enumerate(images):
        space = "/DeviceRGB" if colors == 3 else "/DeviceGray"
        page, content, image = 3 + 3 * index, 4 + 3 * index, 5 + 3 * index
        objects.append(("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Resources "
                        "<< /XObject << /Im1 %d 0 R >> >> /Contents %d 0 R >>"
                        % (PAGE_WIDTH, PAGE_HEIGHT, image, content)).encode("ascii"))
        objects.append(stream_object(b"", image_page_stream()))
        objects.append(stream_object(
            ("/Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace %s "
             "/BitsPerComponent 8 /Filter /FlateDecode /DecodeParms << /Predictor 15 "
             "/Colors %d /BitsPerComponent 8 /Columns %d >>"
             % (width, height, space, colors, width)).encode("ascii"), data))
    Path(path).write_bytes(assemble(objects))
