require 'open3'
require 'time'

module LastModifiedPlugin
  class LastModified < Jekyll::Generator
    safe true
    priority :high

    def generate(site)
      (site.posts.docs + site.pages).each do |page|
        next unless page.data['layout'] == 'post'

        source = File.expand_path(page.path, site.source)
        history, status = Open3.capture2(
          'git', '-C', site.source, 'log', '--follow', '--format=%cI',
          '--', source, err: File::NULL
        )
        next unless status.success? && !history.strip.empty?

        dates = history.lines.map { |date| Time.iso8601(date.strip) }
        # Translated articles are pages, so they have no filename-derived date.
        page.data['date'] ||= dates.last
        published = Time.parse(page.data['date'].to_s)
        page.data['last_modified_at'] ||= [published, dates.first].max
      end
    rescue Errno::ENOENT
      Jekyll.logger.warn 'Post dates:', 'Git unavailable; using front matter dates.'
    end
  end
end
