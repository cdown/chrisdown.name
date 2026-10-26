require 'jekyll'
require 'uglifier'
require_relative '../_plugins/minifier-cache'

module CountMinifications
  def run_uglifyjs(*args)
    $minifications += 1
    super
  end
end
Uglifier.prepend(CountMinifications)

class MinifierCacheTest
  def reset
    MinifierCache::RESULTS.clear
    $minifications = 0
  end

  def assert(condition, message = 'Assertion failed')
    raise message unless condition
  end

  def assert_equal(expected, actual)
    assert(expected == actual, "Expected #{expected.inspect}, got #{actual.inspect}")
  end

  def refute_equal(expected, actual)
    assert(expected != actual)
  end

  def assert_empty(value)
    assert(value.empty?)
  end

  def refute_empty(value)
    assert(!value.empty?)
  end

  def assert_raises(error)
    begin
      yield
    rescue error
      return
    end
    raise "Expected #{error}"
  end

  def test_shared_scripts_are_compiled_once_across_instances_and_aliases
    source = 'function answer() { return 40 + 2; }'
    first = Uglifier.new.compile(source)
    assert_equal first, Uglifier.new.compress(source)
    assert_equal 1, $minifications
    first.replace('changed by caller')
    refute_equal first, Uglifier.new.compile(source)
    assert_equal 1, $minifications
  end

  def test_different_sources_and_options_do_not_share_results
    source = 'function answer() { return 40 + 2; }'
    compact = Uglifier.new.compile(source)
    pretty = Uglifier.new(output: {beautify: true}).compile(source)
    refute_equal compact, pretty
    Uglifier.new.compile('function answer() { return 43; }')
    assert_equal 3, $minifications
  end

  def test_mutated_input_and_options_get_new_keys
    source = +'function answer() { return 42; }'
    options = {output: {beautify: false}}
    compiler = Uglifier.new(options)
    compiler.compile(source)
    source.replace('function answer() { return 43; }')
    compiler.compile(source)
    options[:output][:beautify] = true
    compiler.compile(source)
    assert_equal 3, $minifications
  end

  def test_failed_compilation_is_not_cached
    2.times { assert_raises(Uglifier::Error) { Uglifier.new.compile('function {') } }
    assert_empty MinifierCache::RESULTS
    assert_equal 2, $minifications
  end

  def test_a_new_jekyll_build_clears_the_cache
    Uglifier.new.compile('var answer = 42;')
    refute_empty MinifierCache::RESULTS
    Jekyll::Hooks.trigger(:site, :after_reset, nil)
    assert_empty MinifierCache::RESULTS
  end
end

tests = MinifierCacheTest.new
tests.public_methods.grep(/^test_/).sort.each do |test|
  tests.reset
  tests.public_send(test)
  puts "PASS: #{test}"
end
