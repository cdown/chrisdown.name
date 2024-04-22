class CitationContainer < Liquid::Block
  def render(context)
    site = context.registers[:site]
    converter = site.find_converter_instance(::Jekyll::Converters::Markdown)
    output = converter.convert(super(context))
    "<div class=\"citation-container\">
#{output}
</div>"
  end

  Liquid::Template.register_tag "cc", self
end

