require 'digest'
require 'fileutils'
require 'open3'
require 'tempfile'

# Cache by every renderer input, rather than by the post's modification time.
class Mermaid < Liquid::Block
  def render(context)
    site = context.registers[:site]
    source = super(context)
    config = File.join(site.source, '_scripts/mermaid-config.json')
    key = Digest::SHA256.hexdigest([
      source, File.binread(config), File.binread(__FILE__),
      File.binread(File.join(site.source, 'package-lock.json')),
    ].join("\0"))
    cache = File.join(site.cache_dir, 'mermaid', "#{key}.svg")
    unless File.file?(cache)
      FileUtils.mkdir_p(File.dirname(cache))
      Tempfile.create(['diagram', '.svg'], File.dirname(cache)) do |output|
        command = [File.join(site.source, 'node_modules/.bin/mmdc'),
                   '-i', '-', '-o', output.path, '-c', config,
                   '-I', "mermaid-#{key}", '--no-font-embed',
                   '-b', 'transparent', '-q']
        _, error, status = Open3.capture3(*command, stdin_data: source)
        raise "Mermaid rendering failed: #{error}" unless status.success?
        svg = File.read(output.path)
        raise 'Mermaid did not produce an SVG' unless svg.start_with?('<svg')
        File.write(cache, svg)
      end
    end
    # Keep SVG styles in the document head (and scoped to this diagram's ID).
    page = context.registers[:page]
    page['mermaid_styles'] ||= []
    svg = File.read(cache).gsub(/<style>(.*?)<\/style>/m) do
      page['mermaid_styles'] << Regexp.last_match(1)
      ''
    end
    "<div class=\"mermaid\">#{svg}</div>"
  end

  Liquid::Template.register_tag 'mermaid', self
end
