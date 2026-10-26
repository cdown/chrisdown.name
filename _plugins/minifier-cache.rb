require 'uglifier'

# jekyll-minifier creates a compressor for every page. With ExecJS's Node
# runtime, each compile starts a new process, even for shared layout scripts.
module MinifierCache
  RESULTS = {}

  def compile(source)
    return super unless source.is_a?(String)

    # Copy the input/options into the key so later mutations cannot change it.
    key = Marshal.dump([source, @options])
    RESULTS[key] ||= super.dup.freeze
    RESULTS[key].dup
  end

  # Uglifier's alias would otherwise bypass the prepended compile method.
  def compress(source)
    compile(source)
  end
end

Uglifier.prepend(MinifierCache)
Jekyll::Hooks.register(:site, :after_reset) { MinifierCache::RESULTS.clear }
