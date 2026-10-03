local ID_PREFIX = 'ref-'
local ANCHOR_CLASS = 'bib-anchor'

local EN_DASH = '\226\128\147'

local STEM_MAX_LETTERS = 24
local STEM_PATTERN = '^[A-Za-z]+'
local PLUS_SIGN = '+'
local YEAR_PATTERN = '^%d%d'
local NO_YEAR_PATTERN = '^%-%-'
local LETTER_PATTERN = '^[a-z]'

local function key_at(text, init)
  local _, stem_end = text:find(STEM_PATTERN, init)
  if not stem_end or stem_end - init + 1 > STEM_MAX_LETTERS then return nil end

  local cursor = stem_end + 1
  if text:sub(cursor, cursor) == PLUS_SIGN then cursor = cursor + 1 end

  local _, year_end = text:find(YEAR_PATTERN, cursor)
  if not year_end then _, year_end = text:find(NO_YEAR_PATTERN, cursor) end
  if not year_end then _, year_end = text:find('^' .. EN_DASH, cursor) end
  if not year_end then return nil end

  cursor = year_end + 1
  local _, letter_end = text:find(LETTER_PATTERN, cursor)
  if letter_end then cursor = letter_end + 1 end

  return init, cursor - 1
end

local function keys_in(inner)
  local keys, cursor = {}, 1
  while true do
    local key_start, key_end = key_at(inner, cursor)
    if key_start ~= cursor then return nil end
    table.insert(keys, { text = inner:sub(key_start, key_end),
                         first = key_start, last = key_end })
    cursor = key_end + 1
    if cursor > #inner then return keys end
    local _, separator_end = inner:find('^,%s+', cursor)
    if not separator_end then return nil end
    cursor = separator_end + 1
  end
end

local function anchor_id(key)
  local normalized = key:gsub(EN_DASH, '--')
  return ID_PREFIX .. (normalized:gsub('[^%w]', '-'))
end

local RUN_MEMBER = { Str = true, Space = true, SoftBreak = true }

local function flatten(run)
  local pieces, offsets, lengths = {}, {}, {}
  local offset = 1
  for index, inline in ipairs(run) do
    local piece = (inline.t == 'Str') and inline.text or ' '
    pieces[index] = piece
    offsets[index] = offset
    lengths[index] = #piece
    offset = offset + #piece
  end
  return table.concat(pieces), offsets, lengths
end

local function emit_slice(out, run, offsets, lengths, from, to)
  if to < from then return end
  for index, inline in ipairs(run) do
    local start_offset, length = offsets[index], lengths[index]
    local end_offset = start_offset + length - 1
    if length > 0 and end_offset >= from and start_offset <= to then
      if inline.t == 'Str' then
        local first = math.max(start_offset, from) - start_offset + 1
        local last = math.min(end_offset, to) - start_offset + 1
        table.insert(out, pandoc.Str(inline.text:sub(first, last)))
      else
        table.insert(out, inline)
      end
    end
  end
end

local function context_around(text, from, to)
  local snippet = text:sub(math.max(1, from - 40), math.min(#text, to + 40))
  return (snippet:gsub('%s+', ' '))
end

local function warn(message)
  io.stderr:write('citation-links.lua: ' .. message .. '\n')
end

local anchors = {}
local anchored_by_id = {}
local cited = {}
local unresolved = {}
local unresolved_keys = 0
local linked_count = 0
local anchor_count = 0

local CITATION_ATTR = pandoc.Attr('', { 'citation' }, {})

local function record_unresolved(key, context)
  local report = unresolved[key]
  if report then
    report.count = report.count + 1
  else
    unresolved[key] = { count = 1, context = context }
    unresolved_keys = unresolved_keys + 1
  end
end

local function link_citations(inlines)
  local out = {}
  local list_changed = false
  local index = 1

  while index <= #inlines do
    if not RUN_MEMBER[inlines[index].t] then
      table.insert(out, inlines[index])
      index = index + 1
    else
      local run, run_start = {}, index
      while index <= #inlines and RUN_MEMBER[inlines[index].t] do
        table.insert(run, inlines[index])
        index = index + 1
      end

      local text, offsets, lengths = flatten(run)
      local emitted = {}
      local consumed, cursor = 1, 1
      local run_changed = false

      while true do
        local open_at, close_at = text:find('%b[]', cursor)
        if not open_at then break end

        local keys = keys_in(text:sub(open_at + 1, close_at - 1))

        if not keys then
          cursor = open_at + 1
        else
          local resolvable = {}
          for _, key in ipairs(keys) do
            if anchors[key.text] then
              table.insert(resolvable, key)
            else
              record_unresolved(key.text, context_around(text, open_at, close_at))
            end
          end

          cursor = close_at + 1

          if #resolvable > 0 then
            emit_slice(emitted, run, offsets, lengths, consumed, open_at - 1)

            if #keys == 1 then
              table.insert(emitted, pandoc.Link(
                { pandoc.Str(text:sub(open_at, close_at)) },
                '#' .. anchors[keys[1].text], '', CITATION_ATTR))
            else
              local written = open_at
              for _, key in ipairs(resolvable) do
                emit_slice(emitted, run, offsets, lengths,
                           written, open_at + key.first - 1)
                table.insert(emitted, pandoc.Link({ pandoc.Str(key.text) },
                                                  '#' .. anchors[key.text], '',
                                                  CITATION_ATTR))
                written = open_at + key.last + 1
              end
              emit_slice(emitted, run, offsets, lengths, written, close_at)
            end

            for _, key in ipairs(resolvable) do cited[key.text] = true end
            linked_count = linked_count + #resolvable
            consumed = close_at + 1
            run_changed = true
          end
        end
      end

      if run_changed then
        emit_slice(emitted, run, offsets, lengths, consumed, #text)
        for _, inline in ipairs(emitted) do table.insert(out, inline) end
        list_changed = true
      else
        for offset = run_start, index - 1 do table.insert(out, inlines[offset]) end
      end
    end
  end

  if not list_changed then return nil end
  return pandoc.Inlines(out)
end

local function anchor_entry(block)
  if block.t ~= 'Para' and block.t ~= 'Plain' then return nil end

  local inlines = block.content
  if #inlines == 0 or not RUN_MEMBER[inlines[1].t] then return nil end

  local run = {}
  local index = 1
  while index <= #inlines and RUN_MEMBER[inlines[index].t] do
    table.insert(run, inlines[index])
    index = index + 1
  end

  local text, offsets, lengths = flatten(run)
  local open_at, close_at = text:find('^%b[]')
  if not open_at then return nil end

  local keys = keys_in(text:sub(open_at + 1, close_at - 1))
  if not keys or #keys ~= 1 then return nil end

  local key = keys[1].text
  local id = anchor_id(key)

  if anchors[key] then
    warn(string.format('the bibliography lists [%s] twice. The second entry ' ..
                       'gets no anchor, so every citation lands on the first.',
                       key))
    return nil
  end
  if anchored_by_id[id] then
    warn(string.format('[%s] and [%s] both sanitise to the id "%s", so a ' ..
                       'citation to one would land on the other. [%s] is ' ..
                       'left unanchored and its citations unlinked.',
                       anchored_by_id[id], key, id, key))
    return nil
  end
  anchors[key] = id
  anchored_by_id[id] = key

  local rewritten = { pandoc.Span({ pandoc.Str(text:sub(open_at, close_at)) },
                                  { id = id, class = ANCHOR_CLASS }) }
  emit_slice(rewritten, run, offsets, lengths, close_at + 1, #text)
  for offset = index, #inlines do table.insert(rewritten, inlines[offset]) end

  block.content = pandoc.Inlines(rewritten)
  anchor_count = anchor_count + 1
  return block
end

local references_heading = 'References'

local function read_references_heading(meta)
  local given = meta['build-settings']
  if given and given.references_heading then
    references_heading = pandoc.utils.stringify(given.references_heading)
  end
end

local function is_references_header(block)
  if block.t ~= 'Header' or block.level ~= 1 then return false end
  if block.identifier == references_heading:lower() then return true end
  local text = pandoc.utils.stringify(block):lower():gsub('^%s+', ''):gsub('%s+$', '')
  return text == references_heading:lower()
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

function Pandoc(doc)
  if not is_screen_edition(doc.meta) then return nil end
  read_references_heading(doc.meta)

  local references_at = nil
  for index, block in ipairs(doc.blocks) do
    if is_references_header(block) then
      references_at = index
      break
    end
  end

  if not references_at then
    warn(string.format('no level-1 "%s" heading found, so every citation was ' ..
         'left as plain text. Check that the bibliography file ' ..
         '(manuscript.references in book.yaml) reached the build, that ' ..
         'references_heading matches its heading, and that this filter runs ' ..
         'after digital-mode.lua.', references_heading))
    return nil
  end

  for index = references_at + 1, #doc.blocks do
    local anchored = anchor_entry(doc.blocks[index])
    if anchored then doc.blocks[index] = anchored end
  end

  doc = doc:walk({
    traverse = 'topdown',
    Span = function(span)
      if span.classes:includes(ANCHOR_CLASS) then return span, false end
    end,
    Link = function(link) return link, false end,
    Inlines = link_citations,
  })

  for key, report in pairs(unresolved) do
    warn(string.format('[%s] is cited %d time(s) and has no bibliography ' ..
                       'entry, so it was left as plain text. First seen ' ..
                       'near: ...%s...', key, report.count, report.context))
  end

  local uncited = {}
  for key in pairs(anchors) do
    if not cited[key] then table.insert(uncited, key) end
  end
  table.sort(uncited)
  for _, key in ipairs(uncited) do
    warn(string.format('[%s] has a bibliography entry but is never cited. ' ..
                       'The bibliography holds only what the manuscript cites.',
                       key))
  end

  io.stderr:write(string.format(
    'citation-links.lua: linked %d citations into %d of %d bibliography ' ..
    'entries; %d unresolved key(s), %d uncited entry/entries.\n',
    linked_count, anchor_count - #uncited, anchor_count,
    unresolved_keys, #uncited))

  return doc
end
