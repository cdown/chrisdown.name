class Sidenote < Liquid::Block
  def render(context)
    site = context.registers[:site]
    converter = site.find_converter_instance(::Jekyll::Converters::Markdown)
    output = converter.convert(super(context))

    "<div class=\"sidenote sidenote-right\">
#{output}
</div>"
  end

  Liquid::Template.register_tag "sidenote", self
end
