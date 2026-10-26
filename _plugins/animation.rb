class Animation < Liquid::Block
  def render(context)
    page = context.registers[:page]

    data_json = super(context).strip

    scripts = ""
    unless page["animation_done"]
      page["animation_done"] = true
      scripts = "<script src=\"/js/anime.min.js\"></script>\n" \
                "<script src=\"/js/animation.js\"></script>\n"
    end

    "#{scripts}<div class=\"animation-container\"><script type=\"application/json\">#{data_json}</script></div>"
  end

  Liquid::Template.register_tag "animation", self
end
