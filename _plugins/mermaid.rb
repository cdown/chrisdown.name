class Mermaid < Liquid::Block
  def render(context)
    page = context.registers[:page]

    script = ""
    unless page['mermaid_done']
      page['mermaid_done'] = true
      site = context.registers[:site]
      gitrev = site.data["gitrev"]
      script = "
<script src=\"/js/mermaid.min.js?#{gitrev}\"></script>
<script>
mermaid.initialize({
  theme: 'default',
  themeVariables: {
    fontFamily: '\"Open Sans\", sans-serif',
    clusterBkg: '#fff5ad',
    clusterBorder: '#aaaa33',
    edgeLabelBackground: '#fff5ad',
  }
});
</script>"
    end

    "#{script}<pre class=\"mermaid\">
#{super(context)}
</pre>"
  end

  Liquid::Template.register_tag "mermaid", self
end
