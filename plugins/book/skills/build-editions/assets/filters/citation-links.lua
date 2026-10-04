local ID_PREFIX = 'ref-'
local ANCHOR_CLASS = 'bib-anchor'
local CITATION_CLASS = 'citation'
local URI_CLASS = 'uri'
local EN_DASH = '\226\128\147'
local TRAILING_PUNCTUATION = '^(.-)([,;:]+)$'
local OPENING_PUNCTUATION = '^[%(%[\'"]*'
local NO_BREAK_SPACE = '\194\160'
local ABBREVIATIONS = {}
for _, word in ipairs({
  'aet.', 'aetat.', 'al.', 'Apr.', 'Aug.', 'bk.', 'Bros.', 'c.', 'Capt.', 'cf.', 'ch.',
  'chap.', 'chs.', 'Co.', 'col.', 'Corp.', 'cp.', 'd.', 'Dec.', 'Dr.', 'e.g.', 'ed.', 'eds.',
  'esp.', 'f.', 'fasc.', 'Feb.', 'ff.', 'fig.', 'fl.', 'fol.', 'fols.', 'Fr.', 'Gen.', 'Gov.',
  'Hon.', 'i.e.', 'ill.', 'Inc.', 'incl.', 'Jan.', 'Jr.', 'Jul.', 'Jun.', 'Ltd.', 'M.A.',
  'M.D.', 'Mar.', 'Mr.', 'Mrs.', 'Ms.', 'n.', 'n.b.', 'nn.', 'No.', 'Nov.', 'Oct.', 'p.',
  'Ph.D.', 'pp.', 'Pres.', 'Prof.', 'pt.', 'q.v.', 'Rep.', 'Rev.', 's.v.', 's.vv.', 'saec.',
  'sec.', 'Sen.', 'Sep.', 'Sept.', 'Sgt.', 'Sr.', 'St.', 'univ.', 'viz.', 'vol.', 'vs.',
}) do ABBREVIATIONS[word] = true end
local ELLIPSIS = '\226\128\166'
local MARKUP_TAG = '<(/?)([ib])>'
local BARE_URL = '^(https?://%S-)([%.,;:%)]*)$'
local MARKUP_ELEMENTS = { i = pandoc.Emph, b = pandoc.Strong }
local TEXT_CONTAINERS = { Emph = true, Strong = true, Quoted = true, Span = true }

local function warn(message)
  io.stderr:write('citation-links.lua: ' .. message .. '\n')
end

local function meta_is_true(value)
  if value == nil or value == false then return false end
  if value == true then return true end
  local text = pandoc.utils.stringify(value):lower()
  return text == 'true' or text == 'yes' or text == '1'
end

local function is_screen_edition(meta)
  if FORMAT:match('^epub') or FORMAT:match('^html') then return true end
  return meta_is_true(meta['digital-edition']) or meta_is_true(meta['paper-edition'])
end

local function anchor_id(key)
  local normalized = key:gsub(EN_DASH, '--')
  return ID_PREFIX .. (normalized:gsub('[^%w]', '-'))
end

local function without_prefix(text, prefix)
  if #text > #prefix and text:sub(1, #prefix) == prefix then
    return text:sub(#prefix + 1)
  end
  return nil
end

local function key_of_target(target)
  return without_prefix(target, '#' .. ID_PREFIX)
end

local function key_of_entry(block)
  if block.t ~= 'Div' then return nil end
  return without_prefix(block.identifier, ID_PREFIX)
end

local function bibliography_files(meta)
  local value = meta.bibliography
  if value == nil then return {} end
  if pandoc.utils.type(value) == 'List' then
    local files = {}
    for _, item in ipairs(value) do table.insert(files, pandoc.utils.stringify(item)) end
    return files
  end
  return { pandoc.utils.stringify(value) }
end

local FILTER_ERROR_EXIT = 83

local function stop_build(message)
  io.stderr:write(message, '\n')
  io.stderr:flush()
  os.exit(FILTER_ERROR_EXIT)
end

local function keys_in_bibliography(meta)
  local known = {}
  for _, file in ipairs(bibliography_files(meta)) do
    local handle = io.open(file, 'r')
    if not handle then
      stop_build('citation-links.lua: cannot read the bibliography ' .. file)
    end
    local entries = pandoc.json.decode(handle:read('a'), false)
    handle:close()
    for _, entry in ipairs(entries) do
      if entry.id then known[tostring(entry.id)] = true end
    end
  end
  return known
end

local function sorted_keys(set)
  local list = {}
  for key in pairs(set) do table.insert(list, key) end
  table.sort(list)
  return list
end

local function stop_on_unresolved(unresolved, meta)
  local keys = sorted_keys(unresolved)
  if #keys == 0 then return end
  local source = meta['citation-bibliography-file']
  source = source and pandoc.utils.stringify(source) or 'the bibliography'
  local lines = {}
  for _, key in ipairs(keys) do
    table.insert(lines, string.format('  @%s (cited %d time(s))', key, unresolved[key]))
  end
  local problem = 'have no entry in ' .. source
  if #bibliography_files(meta) == 0 then
    problem = 'are cited, and there is no bibliography at ' .. source
  end
  stop_build(string.format(
    'citation-links.lua: %d key(s) %s:\n%s\n' ..
    'Add each one to the bibliography, or correct the key in the text.',
    #keys, problem, table.concat(lines, '\n')))
end

local function is_abbreviation(inline)
  if inline.t ~= 'Str' then return false end
  return ABBREVIATIONS[inline.text:gsub(OPENING_PUNCTUATION, '')] == true
end

local function joined_after_abbreviations(inlines)
  local out, index = {}, 1
  while index <= #inlines do
    local inline = inlines[index]
    local space, word = inlines[index + 1], inlines[index + 2]
    if is_abbreviation(inline) and space and space.t == 'Space' and word and word.t == 'Str' then
      table.insert(out, pandoc.Str(inline.text .. NO_BREAK_SPACE .. word.text))
      index = index + 3
    else
      table.insert(out, inline)
      index = index + 1
    end
  end
  return pandoc.Inlines(out)
end

local function with_abbreviation_spaces(inlines)
  return pandoc.Inlines(inlines):walk({ Inlines = joined_after_abbreviations })
end

local function split_label(content)
  local first = content[1]
  if not first or first.t ~= 'Str' then return content, {} end
  local label, punctuation = first.text:match(TRAILING_PUNCTUATION)
  local rest = {}
  if label then
    table.insert(rest, pandoc.Str(punctuation))
  else
    label = first.text
  end
  for index = 2, #content do table.insert(rest, content[index]) end
  return { pandoc.Str(label) }, with_abbreviation_spaces(rest)
end

local function is_single_bare_citation(cite)
  local content = cite.content
  return #cite.citations == 1 and #content == 3
     and content[1].t == 'Str' and content[1].text == '['
     and content[2].t == 'Link' and #content[2].content == 1
     and content[2].content[1].t == 'Str'
     and content[3].t == 'Str' and content[3].text == ']'
end

local function citation_link(inlines, key)
  return pandoc.Link(inlines, '#' .. anchor_id(key), '', pandoc.Attr('', { CITATION_CLASS }, {}))
end

local function rewrite_citation(cite, linked, listed)
  if linked and is_single_bare_citation(cite) then
    local key = key_of_target(cite.content[2].target)
    if key and listed[key] then
      local label = cite.content[2].content[1].text
      return { citation_link({ pandoc.Str('[' .. label .. ']') }, key) }
    end
  end
  local out = {}
  for _, inline in ipairs(cite.content) do
    local key = inline.t == 'Link' and key_of_target(inline.target)
    if key then
      local label, rest = split_label(inline.content)
      if linked and listed[key] then
        table.insert(out, citation_link(label, key))
      else
        for _, piece in ipairs(label) do table.insert(out, piece) end
      end
      for _, piece in ipairs(rest) do table.insert(out, piece) end
    else
      table.insert(out, inline)
    end
  end
  return out
end

local function entry_inlines(blocks)
  local inlines = {}
  for _, block in ipairs(blocks) do
    local content
    if block.t == 'Para' or block.t == 'Plain' then
      content = block.content
    elseif block.t == 'Div' then
      content = entry_inlines(block.content)
    end
    if content and #content > 0 then
      if #inlines > 0 then table.insert(inlines, pandoc.Space()) end
      for _, inline in ipairs(content) do table.insert(inlines, inline) end
    end
  end
  return inlines
end

local function without_plain_spans(inlines)
  return pandoc.Inlines(inlines):walk({
    Span = function(span)
      if span.identifier == '' then return span.content end
    end,
    Link = function(link)
      if pandoc.utils.stringify(link.content) == link.target then
        link.classes = { URI_CLASS }
        return link
      end
    end,
  })
end

local function label_length(inlines)
  for index, inline in ipairs(inlines) do
    if inline.t ~= 'Str' then return nil end
    if index == 1 and inline.text:sub(1, 1) ~= '[' then return nil end
    if inline.text:find(']', 1, true) then return index end
  end
  return nil
end

local function with_anchor(inlines, key)
  local attributes = { id = anchor_id(key), class = ANCHOR_CLASS }
  local length = label_length(inlines) or 0
  local label, out = {}, {}
  for index = 1, length do table.insert(label, inlines[index]) end
  table.insert(out, pandoc.Span(label, attributes))
  for index = length + 1, #inlines do table.insert(out, inlines[index]) end
  return out
end

local function markup_pieces(text)
  local pieces, position = {}, 1
  while true do
    local start, finish, closing, tag = text:find(MARKUP_TAG, position)
    if not start then break end
    if start > position then table.insert(pieces, text:sub(position, start - 1)) end
    table.insert(pieces, { closing = closing == '/', tag = tag })
    position = finish + 1
  end
  if position <= #text then table.insert(pieces, text:sub(position)) end
  return pieces
end

local function with_markup_restored(inlines)
  local out, open = {}, nil
  local function add(inline)
    table.insert(open and open.content or out, inline)
  end
  for _, inline in ipairs(inlines) do
    if inline.t == 'Str' and inline.text:find(MARKUP_TAG) then
      for _, piece in ipairs(markup_pieces(inline.text)) do
        if type(piece) == 'string' then
          add(pandoc.Str(piece))
        elseif not piece.closing and not open then
          open = { tag = piece.tag, content = {} }
        elseif piece.closing and open and open.tag == piece.tag then
          table.insert(out, MARKUP_ELEMENTS[open.tag](open.content))
          open = nil
        end
      end
    else
      add(inline)
    end
  end
  if open then
    table.insert(out, pandoc.Str('<' .. open.tag .. '>'))
    for _, inline in ipairs(open.content) do table.insert(out, inline) end
  end
  return out
end

local function with_bare_links(inlines)
  local out = {}
  for _, inline in ipairs(inlines) do
    local url, trailing
    if inline.t == 'Str' then url, trailing = inline.text:match(BARE_URL) end
    if url then
      table.insert(out, pandoc.Link({ pandoc.Str(url) }, url, '', pandoc.Attr('', { URI_CLASS }, {})))
      if trailing ~= '' then table.insert(out, pandoc.Str(trailing)) end
    else
      table.insert(out, inline)
    end
  end
  return out
end

local function with_ellipses(inlines)
  local out = {}
  for _, inline in ipairs(inlines) do
    if inline.t == 'Str' then
      table.insert(out, pandoc.Str((inline.text:gsub('%.%.%.', ELLIPSIS))))
    else
      if TEXT_CONTAINERS[inline.t] then inline.content = with_ellipses(inline.content) end
      table.insert(out, inline)
    end
  end
  return out
end

local function entry_text(blocks)
  local inlines = without_plain_spans(entry_inlines(blocks))
  inlines = with_ellipses(with_bare_links(with_markup_restored(inlines)))
  return with_abbreviation_spaces(inlines)
end

local function reference_paragraphs(reference_list, linked)
  local paragraphs = {}
  for _, entry in ipairs(reference_list.content) do
    local key = key_of_entry(entry)
    if key then
      local inlines = entry_text(entry.content)
      if linked then inlines = with_anchor(inlines, key) end
      table.insert(paragraphs, pandoc.Para(inlines))
    end
  end
  return paragraphs
end

local function is_reference_list(div)
  return div.identifier == 'refs' or div.classes:includes('csl-bib-body')
end

local function listed_keys(doc)
  local listed, count = {}, 0
  doc:walk({
    Div = function(div)
      if not is_reference_list(div) then return nil end
      for _, entry in ipairs(div.content) do
        local key = key_of_entry(entry)
        if key and not listed[key] then
          listed[key] = true
          count = count + 1
        end
      end
    end,
  })
  return listed, count
end

local function cited_keys(doc, known)
  local cited, unresolved, count = {}, {}, 0
  doc:walk({
    Cite = function(cite)
      for _, citation in ipairs(cite.citations) do
        count = count + 1
        cited[citation.id] = true
        if not known[citation.id] then
          unresolved[citation.id] = (unresolved[citation.id] or 0) + 1
        end
      end
    end,
  })
  return cited, unresolved, count
end

function Pandoc(doc)
  local linked = is_screen_edition(doc.meta)
  local listed, listed_count = listed_keys(doc)
  local cited, unresolved, citation_count = cited_keys(doc, keys_in_bibliography(doc.meta))
  stop_on_unresolved(unresolved, doc.meta)

  doc = doc:walk({
    Cite = function(cite) return rewrite_citation(cite, linked, listed) end,
    Div = function(div)
      if is_reference_list(div) then return reference_paragraphs(div, linked) end
    end,
  })

  if citation_count > 0 and listed_count == 0 then
    warn('the files built hold no reference list (no "::: {#refs}" div), so ' ..
         'no reference list was printed and every citation is plain text.')
  end
  io.stderr:write(string.format(
    'citation-links.lua: %d citation(s) of %d key(s) %s %d bibliography ' ..
    'entries; 0 unresolved keys.\n',
    citation_count, #sorted_keys(cited),
    (linked and listed_count > 0) and 'linked to' or 'as plain text, with',
    listed_count))

  return doc
end
