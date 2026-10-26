require 'cgi'

module VideoFacade
  def self.render(context, embed, watch, provider)
    page = context.registers[:page]
    page['video_facades'] = true
    title = CGI.escapeHTML("#{page['title']} (#{provider} video)")
    embed, watch = CGI.escapeHTML(embed), CGI.escapeHTML(watch)
    "<div class=\"video-facade\"><div class=\"youtube-container\">" \
      "<a class=\"video-load\" href=\"#{watch}\" data-video-src=\"#{embed}\" " \
      "data-video-title=\"#{title}\">&#9654; Play #{provider} video</a></div>" \
      "<p class=\"video-direct\"><a href=\"#{watch}\">Open video on #{provider}</a></p></div>"
  end
end
