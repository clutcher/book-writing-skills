local SOUL_HOSTILE = {
  Code = true,
  Math = true,
  Link = true,
  Image = true,
  RawInline = true,
  Cite = true,
  Strikeout = true,
}

local SOUL_CONTAINER = {
  Emph = true,
  Strong = true,
  Underline = true,
  SmallCaps = true,
  Superscript = true,
  Subscript = true,
  Span = true,
}

local SOUL_UNSAFE_CHAR = {
  ["\u{2018}"] = "\\textquoteleft{}",
  ["\u{2019}"] = "\\textquoteright{}",
  ["\u{201C}"] = "\\textquotedblleft{}",
  ["\u{201D}"] = "\\textquotedblright{}",
  ["\u{2013}"] = "\\textendash{}",
  ["\u{2014}"] = "\\textemdash{}",
  ["\u{2026}"] = "\\textellipsis{}",
}

local SOUL_SAFE_MAX_CODEPOINT = 0xFF

local function split_chars(text)
  local chars = {}
  for char in text:gmatch(utf8.charpattern) do
    chars[#chars + 1] = char
  end
  return chars
end

local function trailing_unsafe_start(chars)
  local first = #chars + 1
  while first > 1 and utf8.codepoint(chars[first - 1]) > SOUL_SAFE_MAX_CODEPOINT do
    first = first - 1
  end
  return first
end

local QUOTE_MACROS = {
  DoubleQuote = { "\\textquotedblleft{}", "\\textquotedblright{}" },
  SingleQuote = { "\\textquoteleft{}", "\\textquoteright{}" },
}

local function soul_safe_string(text)
  local out = pandoc.List({})
  local plain = {}
  local function flush_plain()
    if #plain > 0 then
      out:insert(pandoc.Str(table.concat(plain)))
      plain = {}
    end
  end
  local chars = split_chars(text)
  local unsafe_from = trailing_unsafe_start(chars)
  for index, char in ipairs(chars) do
    local macro = SOUL_UNSAFE_CHAR[char]
    if macro then
      flush_plain()
      out:insert(pandoc.RawInline("latex", macro))
    elseif index >= unsafe_from then
      flush_plain()
      out:insert(pandoc.RawInline("latex", "\\soulomit{" .. char .. "}"))
    else
      plain[#plain + 1] = char
    end
  end
  flush_plain()
  return out
end

local function protect_for_soul(inlines)
  local out = pandoc.List({})
  for _, el in ipairs(inlines) do
    if el.t == "Str" then
      out:extend(soul_safe_string(el.text))
    elseif el.t == "Quoted" then
      local macros = QUOTE_MACROS[el.quotetype]
      out:insert(pandoc.RawInline("latex", macros[1]))
      out:extend(protect_for_soul(el.content))
      out:insert(pandoc.RawInline("latex", macros[2]))
    elseif SOUL_HOSTILE[el.t] then
      out:insert(pandoc.RawInline("latex", "\\mbox{"))
      out:insert(el)
      out:insert(pandoc.RawInline("latex", "}"))
    elseif el.t == "Note" then
      out:insert(pandoc.RawInline("latex", "}"))
      out:insert(el)
      out:insert(pandoc.RawInline("latex", "\\added{"))
    elseif SOUL_CONTAINER[el.t] and el.content then
      el.content = protect_for_soul(el.content)
      out:insert(el)
    else
      out:insert(el)
    end
  end
  return out
end

function Span(el)
  for _, cls in ipairs(el.classes) do
    if cls == "added" then
      local out = pandoc.List({ pandoc.RawInline("latex", "\\added{") })
      out:extend(protect_for_soul(el.content))
      out:insert(pandoc.RawInline("latex", "}"))
      return out
    end
  end
end

local BOX_HOISTED = {
  Header = true,
  RawBlock = true,
}

function Div(el)
  for _, cls in ipairs(el.classes) do
    if cls == "added" then
      local out = pandoc.List({})
      local boxed = pandoc.List({})

      local function flush()
        if #boxed == 0 then return end
        out:insert(pandoc.RawBlock("latex", "\\begin{addedblock}"))
        out:extend(boxed)
        out:insert(pandoc.RawBlock("latex", "\\end{addedblock}"))
        boxed = pandoc.List({})
      end

      for _, block in ipairs(el.content) do
        if BOX_HOISTED[block.t] then
          flush()
          out:insert(block)
        else
          boxed:insert(block)
        end
      end
      flush()

      return out
    end
  end
end
