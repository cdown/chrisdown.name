class YouTube < Liquid::Tag
  Syntax = /^\s*([^\s]+)(\s+(\d+)\s+(\d+)\s*)?/

  def initialize(tagName, markup, tokens)
    super

    if markup =~ Syntax then
      @id = $1
      raise 'Invalid YouTube video ID' unless @id.match?(/\A[A-Za-z0-9_-]{11}\z/)
    else
      raise 'No YouTube ID provided in the "youtube" tag'
    end
  end

  def render(context)
    VideoFacade.render(context, "https://www.youtube.com/embed/#{@id}?autoplay=1",
                       "https://www.youtube.com/watch?v=#{@id}", 'YouTube')
  end

  Liquid::Template.register_tag "youtube", self
end
