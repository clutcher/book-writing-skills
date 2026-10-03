local references_heading = 'References'

local function read_references_heading(meta)
  local given = meta['build-settings']
  if given and given.references_heading then
    references_heading = pandoc.utils.stringify(given.references_heading)
  end
end

local function is_references_header(block)
  if block.level ~= 1 then return false end
  local text = pandoc.utils.stringify(block):lower():gsub('^%s+', ''):gsub('%s+$', '')
  return text == references_heading:lower()
end

function Pandoc(doc)
  read_references_heading(doc.meta)
  local unnumbered = 0
  doc.blocks = doc.blocks:walk({
    Header = function(block)
      if not is_references_header(block) then return nil end
      if not block.classes:includes('unnumbered') then
        block.classes:insert('unnumbered')
      end
      unnumbered = unnumbered + 1
      return block
    end,
  })
  io.stderr:write(string.format(
    'paper-mode.lua: %d "%s" heading(s) left unnumbered.\n', unnumbered, references_heading))
  return doc
end
