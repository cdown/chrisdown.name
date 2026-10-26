require 'liquid'
require_relative '../_plugins/video'
require_relative '../_plugins/youtube'
require_relative '../_plugins/fbvideo'

page = {'title' => 'A "quoted" title & more'}
render = lambda do |source|
  Liquid::Template.parse(source).render!({}, registers: {page: page})
end
youtube = render.call('{% youtube ikZ8_mRotT4 %}')
raise 'Missing direct YouTube fallback' unless youtube.include?('https://www.youtube.com/watch?v=ikZ8_mRotT4')
raise 'Eager iframe' if youtube.include?('<iframe')
raise 'Unescaped title' unless youtube.include?('&quot;quoted&quot; title &amp; more')
raise 'Script not requested' unless page['video_facades']
facebook = render.call('{% fbvideo https://www.facebook.com/plugins/video.php?href=https%3A%2F%2Fwww.facebook.com%2Ftest%2Fvideos%2F123 %}')
raise 'Missing direct Facebook fallback' unless facebook.include?('href="https://www.facebook.com/test/videos/123"')
raise 'Eager iframe' if facebook.include?('<iframe')
['{% youtube invalid %}', '{% fbvideo https://example.org/embed %}'].each do |source|
  begin
    render.call(source)
    raise 'Expected invalid video URL to be rejected'
  rescue RuntimeError => error
    raise unless ['Invalid YouTube video ID', 'Invalid Facebook video embed URL'].include?(error.message)
  end
end
puts 'PASS: Video facades, direct links, escaped titles and invalid URL rejection'
