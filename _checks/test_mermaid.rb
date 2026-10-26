require 'liquid'
require 'tmpdir'
require 'json'
require_relative '../_plugins/mermaid'

def assert(value, message)
  raise message unless value
end

Dir.mktmpdir do |root|
  FileUtils.mkdir_p(File.join(root, '_scripts'))
  config = File.join(root, '_scripts/mermaid-config.json')
  lock = File.join(root, 'package-lock.json')
  File.write(config, '{}')
  File.write(lock, '{}')
  site = Struct.new(:source, :cache_dir).new(root, File.join(root, 'cache'))
  calls = []
  failure = false
  invalid = false
  original = Open3.method(:capture3)
  Open3.define_singleton_method(:capture3) do |*command, stdin_data:|
    calls << stdin_data
    output = command[command.index('-o') + 1]
    File.write(output, invalid ? '' : "<svg><title>#{stdin_data.strip}</title></svg>")
    ['', 'renderer error', Struct.new(:success?).new(!failure)]
  end
  render = lambda do |source|
    Liquid::Template.parse("{% mermaid %}#{source}{% endmermaid %}").render!(
      {}, registers: {site: site, page: {}})
  end
  begin
    first = render.call('graph TD; A-->B')
    assert(first == render.call('graph TD; A-->B'), 'Cached output changed')
    assert(calls.size == 1, 'Same diagram rendered twice')
    render.call('graph TD; A-->C')
    assert(calls.size == 2, 'Source changes must render again')
    File.write(config, '{"theme":"dark"}')
    render.call('graph TD; A-->B')
    assert(calls.size == 3, 'Configuration changes must render again')
    File.write(lock, '{"new":"dependency"}')
    render.call('graph TD; A-->B')
    assert(calls.size == 4, 'Dependency changes must render again')
    failure = true
    2.times do
      begin
        render.call('invalid diagram')
        raise 'Renderer failure was ignored'
      rescue RuntimeError => error
        assert(error.message.include?('renderer error'), error.message)
      end
    end
    assert(calls.size == 6, 'Renderer failures must not be cached')
    failure = false
    invalid = true
    begin
      render.call('empty output')
      raise 'Invalid renderer output was accepted'
    rescue RuntimeError => error
      assert(error.message.include?('did not produce an SVG'), error.message)
    end
    puts 'PASS: Mermaid reuse, source/config/dependency invalidation, failure retry and output validation'
  ensure
    Open3.define_singleton_method(:capture3, original)
  end
end
