local DROP_WITH_ARGS = {
  'thispagestyle', 'setlength', 'bookmarksetup', 'pagestyle',
  'addcontentsline', 'markboth', 'phantomsection', 'vspace', 'pdfbookmark',
}

local DROP_BARE = {
  'vfill', 'medskip', 'bigskip', 'smallskip', 'newpage', 'clearpage',
  'cleardoublepage', 'par', 'begingroup', 'endgroup', 'noindent', 'centering',
  'small', 'footnotesize', 'normalsize', 'large', 'Large', 'huge', 'Huge',
  'backmatter', 'frontmatter', 'mainmatter', 'tableofcontents', 'relax',
}

local LANGUAGE_CODES = {
  latin = 'la', french = 'fr', german = 'de', spanish = 'es', italian = 'it',
}

local HEADING_TYPES = {
  ['Preface'] = 'preface',
  ['Acknowledgments'] = 'acknowledgments',
  ['References'] = 'bibliography',
}

local settings = {
  chapter_heading_word = 'Chapter',
  front_matter_pages = { 'Dedication', 'Epigraph' },
  copyright_markers = { 'rights reserved', 'ISBN' },
  emblem_alt = 'Publisher emblem',
}

local SETTINGS_KEY = 'build-settings'
local CONFIG_HINT = 'book.yaml (under book:)'

local function meta_text(value)
  if value == nil then return nil end
  return pandoc.utils.stringify(value)
end

local function meta_list(value)
  if value == nil then return nil end
  if pandoc.utils.type(value) ~= 'List' then return { meta_text(value) } end
  local items = {}
  for _, item in ipairs(value) do table.insert(items, meta_text(item)) end
  return items
end

local function merge_map(target, value)
  if value == nil then return end
  for key, item in pairs(value) do target[key] = meta_text(item) end
end

local function append_list(target, value)
  for _, item in ipairs(meta_list(value) or {}) do table.insert(target, item) end
end

local function read_settings(meta)
  local given = meta[SETTINGS_KEY]
  if given == nil then return nil end
  append_list(DROP_WITH_ARGS, given.latex_commands_to_drop)
  merge_map(LANGUAGE_CODES, given.language_codes)
  merge_map(HEADING_TYPES, given.heading_types)
  settings.chapter_heading_word = meta_text(given.chapter_heading_word) or settings.chapter_heading_word
  settings.front_matter_pages = meta_list(given.front_matter_pages) or settings.front_matter_pages
  settings.copyright_markers = meta_list(given.copyright_markers) or settings.copyright_markers
  settings.emblem_alt = meta_text(given.emblem_alt) or settings.emblem_alt
  return nil
end

local function strip_comments(text)
  local out = {}
  for line in (text .. '\n'):gmatch('([^\n]*)\n') do
    local cleaned = line:gsub('([^\\])%%.*$', '%1'):gsub('^%%.*$', '')
    table.insert(out, cleaned)
  end
  return table.concat(out, '\n')
end

local function drop_command(text, name)
  local pattern = '\\' .. name
  while true do
    local s = text:find(pattern .. '[^a-zA-Z]', 1, false)
    if not s then
      s = text:find(pattern .. '$', 1, false)
      if not s then break end
    end
    local i = s + #pattern
    if text:sub(i, i) == '*' then i = i + 1 end
    while text:sub(i, i) == '[' do
      local close = text:find(']', i, true)
      if not close then break end
      i = close + 1
    end
    while text:sub(i, i) == '{' do
      local depth, j = 0, i
      repeat
        local c = text:sub(j, j)
        if c == '{' then depth = depth + 1
        elseif c == '}' then depth = depth - 1
        elseif c == '' then break end
        j = j + 1
      until depth == 0
      i = j
    end
    text = text:sub(1, s - 1) .. text:sub(i)
  end
  return text
end

local function to_markdown(text)
  text = text:gsub('\\langtext%s*(%b{})%s*(%b{})', function(lang, body)
    local name = lang:sub(2, -2)
    local code = LANGUAGE_CODES[name]
    if not code then
      error(string.format(
        'digital-mode.lua: \\langtext{%s} has no BCP 47 language code. Add ' ..
        '%s to language_codes in %s rather than letting the passage inherit ' ..
        'the book language.', name, name, CONFIG_HINT))
    end
    return '[' .. body:sub(2, -2) .. ']{lang=' .. code .. '}'
  end)
  text = text:gsub('\\textcopyright%s*~?', '\u{00A9} ')
  text = text:gsub('\\textit%s*(%b{})', function(g) return '*' .. g:sub(2, -2) .. '*' end)
  text = text:gsub('\\emph%s*(%b{})',   function(g) return '*' .. g:sub(2, -2) .. '*' end)
  text = text:gsub('\\textbf%s*(%b{})', function(g) return '**' .. g:sub(2, -2) .. '**' end)
  text = text:gsub('\\\\%s*\n', '\\\n')
  text = text:gsub('~', ' ')
  return text
end

local function assert_no_latex_left(text, context)
  local leftover = text:match('\\([a-zA-Z]+)')
  if leftover then
    error(string.format(
      'digital-mode.lua: unhandled LaTeX command \\%s in a raw block%s.\n' ..
      'This filter refuses to guess. Either add %s to latex_commands_to_drop ' ..
      'in %s (when it only shapes the printed page), or rewrite the block in ' ..
      'markdown.\nBlock was:\n%s',
      leftover, context and (' (' .. context .. ')') or '', leftover, CONFIG_HINT, text))
  end
end

local function parse_prose(text, context)
  text = to_markdown(text)
  assert_no_latex_left(text, context)
  if text:match('^%s*$') then return {} end
  return pandoc.read(text, 'markdown').blocks
end

local function file_exists(path)
  local handle = io.open(path, 'r')
  if not handle then return false end
  handle:close()
  return true
end

local function image_from(path)
  local png = path:gsub('%.pdf$', '.png')
  local svg = path:gsub('%.pdf$', '.svg')
  local chosen = file_exists(png) and png or svg
  return pandoc.Para({ pandoc.Image({ pandoc.Str(settings.emblem_alt) }, chosen) })
end

local function drop_layout_commands(text)
  for _, name in ipairs(DROP_WITH_ARGS) do text = drop_command(text, name) end
  for _, name in ipairs(DROP_BARE) do text = drop_command(text, name) end
  return text
end

local function apply_epub_semantics(header, epub_type)
  if not FORMAT:match('epub') then return header end
  header.attributes['epub:type'] = epub_type
  if epub_type == 'bibliography' then
    header.attributes['role'] = 'doc-bibliography'
  end
  if epub_type == 'chapter' then
    header.classes:insert('chapter')
  end
  if epub_type == 'bibliography' then
    header.classes:insert('bibliography')
  end
  return header
end

local ROMAN_STEPS = {
  { 100, 'C' }, { 90, 'XC' }, { 50, 'L' }, { 40, 'XL' },
  { 10, 'X' }, { 9, 'IX' }, { 5, 'V' }, { 4, 'IV' }, { 1, 'I' },
}

local function roman_numeral(value)
  local out = {}
  for _, step in ipairs(ROMAN_STEPS) do
    while value >= step[1] do
      table.insert(out, step[2])
      value = value - step[1]
    end
  end
  return table.concat(out)
end

local parts_seen = 0

local function translate(text)
  text = strip_comments(text)
  text = drop_layout_commands(text)

  local blocks = {}
  local pos = 1

  local function flush_prose(upto)
    local chunk = text:sub(pos, upto)
    for _, b in ipairs(parse_prose(chunk)) do table.insert(blocks, b) end
  end

  while true do
    local ps, pe, title = text:find('\\part%s*{(.-)}', pos)
    local cs, ce, centered = text:find('\\begin{center}(.-)\\end{center}', pos)
    local ts, te, tikz = text:find('\\begin{tikzpicture}(.-)\\end{tikzpicture}', pos)

    local first, kind = nil, nil
    local function consider(s, k) if s and (not first or s < first) then first, kind = s, k end end
    consider(ps, 'part'); consider(cs, 'center'); consider(ts, 'tikz')

    if not first then break end

    flush_prose(first - 1)

    if kind == 'part' then
      parts_seen = parts_seen + 1
      local labelled = 'Part ' .. roman_numeral(parts_seen) .. ': ' .. title
      local title_inlines = pandoc.utils.blocks_to_inlines(parse_prose(labelled))
      local header = pandoc.Header(1, title_inlines, { class = 'part' })
      table.insert(blocks, apply_epub_semantics(header, 'part'))
      pos = pe + 1
    elseif kind == 'center' then
      table.insert(blocks, pandoc.Div(parse_prose(centered), { class = 'center' }))
      pos = ce + 1
    else
      local path = tikz:match('\\includegraphics%s*%b[]%s*{(.-)}')
                or tikz:match('\\includegraphics%s*{(.-)}')
      if path then table.insert(blocks, image_from(path)) end
      pos = te + 1
    end
  end

  for _, b in ipairs(parse_prose(text:sub(pos))) do table.insert(blocks, b) end

  return blocks
end

local REFERENCE_COLUMNS = 36
local COMFORTABLE_SCALE = 0.60

local function widest_line(text)
  local widest = 0
  for line in (text .. '\n'):gmatch('([^\n]*)\n') do
    local width = utf8.len(line) or #line
    if width > widest then widest = width end
  end
  return widest
end

local function fit_ascii_diagram(el)
  if FORMAT:match('latex') or FORMAT:match('beamer') then return nil end
  if not el.classes:includes('ascii') then return nil end

  local widest = widest_line(el.text)
  if widest <= REFERENCE_COLUMNS then return nil end

  local scale = REFERENCE_COLUMNS / widest
  if scale < COMFORTABLE_SCALE then
    io.stderr:write(string.format(
      'digital-mode.lua: ASCII diagram is %d columns wide; fitting it needs ' ..
      '%.2fem, below the %.2fem comfortable size. Fitted anyway (clipping would ' ..
      'be worse), but this one is worth narrowing in the manuscript or ' ..
      'redrawing as SVG.\n',
      widest, scale, COMFORTABLE_SCALE))
  end

  el.attributes['style'] = string.format('font-size:%.2fem', scale)
  return el
end

local unlabelled_seen = 0

local function contains_any(text, markers)
  for _, marker in ipairs(markers) do
    if text:find(marker, 1, true) then return true end
  end
  return false
end

local function is_copyright(blocks)
  local text = pandoc.utils.stringify(pandoc.Pandoc(blocks))
  return contains_any(text, settings.copyright_markers)
end

local function move_emblem_last(blocks)
  local emblem, rest = nil, {}
  for _, b in ipairs(blocks) do
    if not emblem and b.t == 'Para' and #b.content == 1
       and (b.content[1].t == 'Image' or b.content[1].t == 'RawInline') then
      emblem = b
    else
      table.insert(rest, b)
    end
  end
  if emblem then
    table.insert(rest, pandoc.Div({ emblem }, { class = 'emblem' }))
  end
  return rest
end

local function as_front_matter_section(blocks)
  if #blocks == 0 then return blocks end

  local label, class
  if is_copyright(blocks) then
    label, class = 'Copyright', 'copyright-page'
    blocks = move_emblem_last(blocks)
  else
    unlabelled_seen = unlabelled_seen + 1
    label = settings.front_matter_pages[unlabelled_seen]
    if not label then return blocks end
    class = label:lower()
  end

  local heading = pandoc.Header(1, { pandoc.Str(label) },
                                { class = 'fm-heading', id = 'fm-' .. class })
  local out = { apply_epub_semantics(heading, class) }
  for _, b in ipairs(blocks) do table.insert(out, b) end
  return { pandoc.Div(out, { class = 'front-matter ' .. class }) }
end

local function semantics_for_heading(text)
  local named = HEADING_TYPES[text]
  if named then return named end
  if text:match('^' .. settings.chapter_heading_word .. '%s+%d+') then return 'chapter' end
  return nil
end

local function label_top_heading(el)
  if not FORMAT:match('epub') then return nil end
  if el.level ~= 1 then return nil end
  if el.attributes['epub:type'] then return nil end

  local text = pandoc.utils.stringify(el.content)
  local epub_type = semantics_for_heading(text)
  if not epub_type then
    io.stderr:write(string.format(
      'digital-mode.lua: no EPUB semantics for the top-level heading "%s". ' ..
      'It reads correctly, but its section carries no epub:type and its file ' ..
      'falls back to bodymatter. Add it to heading_types in %s.\n', text, CONFIG_HINT))
    return nil
  end

  return apply_epub_semantics(el, epub_type)
end

local function translate_raw_block(el)
  if el.format ~= 'latex' and el.format ~= 'tex' then return nil end
  if FORMAT:match('latex') or FORMAT:match('beamer') then return nil end

  local blocks = translate(el.text)
  if #blocks == 0 then return blocks end
  if blocks[1].t == 'Header' then return blocks end
  return as_front_matter_section(blocks)
end

local function scope_table_heads(tbl)
  if not FORMAT:match('epub') and not FORMAT:match('html') then return nil end

  for _, row in ipairs(tbl.head.rows) do
    for _, cell in ipairs(row.cells) do
      cell.attr.attributes['scope'] = 'col'
    end
  end
  return tbl
end

return {
  { Meta = read_settings },
  {
    CodeBlock = fit_ascii_diagram,
    Header = label_top_heading,
    RawBlock = translate_raw_block,
    Table = scope_table_heads,
  },
}
