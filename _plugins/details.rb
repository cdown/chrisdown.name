class Details < Liquid::Block
  def initialize(tag_name, markup, tokens)
    @title = markup
    super
  end

  def render(context)
    contents = super

    # Pipe param through liquid to make additional replacements possible
    content = Liquid::Template.parse(contents).render context

    "<details markdown=1><summary>#{@title}</summary>
#{content}
</details>"
  end

  Liquid::Template.register_tag "details", self
end
