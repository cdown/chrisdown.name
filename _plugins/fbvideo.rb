require 'uri'

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
    uri = URI.parse(@url)
    unless uri.scheme == 'https' && uri.host == 'www.facebook.com' && uri.path == '/plugins/video.php'
      raise 'Invalid Facebook video embed URL'
    end
    watch = URI.decode_www_form(uri.query || '').to_h['href']
    unless watch&.start_with?('https://www.facebook.com/')
      raise 'Missing Facebook video watch URL'
    end
    VideoFacade.render(context, @url, watch, 'Facebook')
  end

  Liquid::Template.register_tag "fbvideo", self
end
