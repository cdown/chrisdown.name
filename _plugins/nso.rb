class NonSidenoteOnly < Liquid::Block
  def render(context)
    "<span class=\"non-sidenote-only\">#{super(context)}</span>"
  end

  Liquid::Template.register_tag "nso", self
end
