class YouTube < Liquid::Tag
  Syntax = /^\s*([^\s]+)(\s+(\d+)\s+(\d+)\s*)?/

  def initialize(tagName, markup, tokens)
    super

    if markup =~ Syntax then
      @id = $1
    else
      raise 'No YouTube ID provided in the "youtube" tag'
    end
  end

  def render(context)
    "<div class=\"youtube-container\">
         <iframe allowfullscreen=\"allowfullscreen\"
          src=\"//www.youtube.com/embed/#{@id}\"> </iframe>
     </div>"
  end

  Liquid::Template.register_tag "youtube", self
end
