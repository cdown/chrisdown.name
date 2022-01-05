class YouTube < Liquid::Tag
  Syntax = /^\s*([^\s]+)(\s+(\d+)\s+(\d+)\s*)?/

  def initialize(tagName, markup, tokens)
    super

    if markup =~ Syntax then
      @id = $1
    else
      raise 'No YouTube ID provided in the "youtube" tag'
    end
  end

  def render(context)
    %Q{
<script type="text/javascript">
var ytcss_id = "ytcss";
if (!document.getElementById(ytcss_id)) {
  var link = document.createElement("link");
  link.href = "/css/lite-yt-embed.css";
  link.id = ytcss_id;
  link.type = "text/css";
  link.rel = "stylesheet";
  document.getElementsByTagName("head")[0].appendChild(link);
}
</script>
<script src="/js/lite-yt-embed.js"></script>
<lite-youtube videoid="#{@id}" playlabel="Play"></lite-youtube>
    }
  end

  Liquid::Template.register_tag "youtube", self
end
