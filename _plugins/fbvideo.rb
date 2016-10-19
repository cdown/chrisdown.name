class FbVideo < Liquid::Tag
  Syntax = /^\s*([^\s]+)(\s+(\d+)\s+(\d+)\s*)?/

  def initialize(tagName, markup, tokens)
    super

    if markup =~ Syntax then
      @url = $1
    else
      raise 'No FB video embed URL provided in the "fbvideo" tag'
    end
  end

  def render(context)
    "<div class=\"youtube-container\">
         <iframe allowfullscreen=\"allowfullscreen\"
          src=\"#{@url}\"> </iframe>
     </div>"
  end

  Liquid::Template.register_tag "fbvideo", self
end
