require 'date'
require 'fileutils'

task :default => [:deploy]

gzip_hdr = "Content-Encoding: gzip"
cc_hdr = "Cache-Control: public, max-age=%d"

# With charset
html_hdr = "Content-Type: text/html; charset=utf-8"
css_hdr = "Content-Type: text/css; charset=utf-8"
ta_hdr = "Content-Type: application/trafficadvice+json; charset=utf-8"
rss_hdr = "Content-Type: application/rss+xml; charset=utf-8"

# 1 hour for anything unspecified
generic_cc = cc_hdr % (60 * 60)
generic_excludes = ""

# 24 hours for static content
static_cc = cc_hdr % (24 * 60 * 60)
static_includes = ""
["css/*", "images/*", "fonts/*", "photos/*", "talks/*"].each do |path|
  static_includes += " --include '#{path}' "
  generic_excludes += " --exclude '#{path}' "
end

gzip_includes = ""
find_names_arr = []
["*.html", "*.css", "*.js"].each do |path|
  gzip_includes += " --include '#{path}' "
  find_names_arr.push("-name '#{path}'")
end
find_names = '\( ' + find_names_arr.join(" -or ") + ' \)'

# 5 minutes for posts written in the last 7 days, as updates may be more
# frequent
this_week_post_cc = cc_hdr % (5 * 60)
this_week_post_includes = ""
(Date.today-6..Date.today).map do |date|
  date_glob = date.strftime("%Y/%m/%d") + "/*"
  this_week_post_includes += " --include '#{date_glob}' "
  generic_excludes += " --exclude '#{date_glob}' "
end

# HACK: s3cmd modify returns 1 if there was nothing matched, what? This will
# get overwritten by the next step, but ugh...
this_week_post_includes += " --include 404.html "

# Cache 404s for 2 minutes, since if something is broken we want to fix it
# fast, but a mass storm to S3 backend should still be avoided
enoent_cc = cc_hdr % (2 * 60)
generic_excludes += " --exclude 404.html "

# These files must exist to avoid being deleted by --delete-removed
redirects = {
  "swap" => "/2018/01/02/in-defence-of-swap.html",
  "swap-ja" => "/ja/2018/01/02/in-defence-of-swap.html",
  "ssl" => "/2016/02/17/lessons-learned-running-ssl-at-scale.html",
  "srt" => "/2016/09/04/cleaning-up-muxing-extracting-subtitles-using-ffmpeg-srt-tools.html",
  "cgroupv2" => "/2017/03/01/cgroupv2-linux-new-cgroup-hierarchy.html",
  "squashfs" => "/2018/04/17/kernel-adventures-the-curious-case-of-squashfs-stalls.html",
  "lmmas" => "/2019/07/18/linux-memory-management-at-scale.html",
  "numbers" => "/2020/01/13/1195725856-and-friends-the-origins-of-mysterious-numbers.html",
  "1195725856" => "/2020/01/13/1195725856-and-friends-the-origins-of-mysterious-numbers.html",
  "tmpfs" => "/2021/07/02/tmpfs-inode-corruption-introducing-inode64.html",
  "2020/01/13/1195725856-other-mysterious-numbers.html" => "/2020/01/13/1195725856-and-friends-the-origins-of-mysterious-numbers.html",

  # Frequent 404s
  "feed" => "/feed.xml",
  "rss" => "/feed.xml",
  "feeds" => "/feed.xml",
}

task :create_local_redirects => :build do
  redirects.each do |from, to|
    loc = "_deploy/" + from
    if File.exist?(loc)
      raise "Redirect stub would overwrite #{loc}"
    end

    unless File.file?(Dir.pwd + "/_deploy/" + to)
      raise "Missing redirect target to #{to}"
    end

    if loc.end_with?(".html")
      # Old redirects that used to be handled by jekyll-redirect-from
      FileUtils.mkdir_p(File.dirname(loc))
      File.open(loc, "w") {}
    else
      Dir.mkdir(loc)
      File.open(loc + "/index.html", "w") {}
    end
  end
end

task :sync => :build do
  # First pass for gzipped content only, second will leave them alone
  sh "s3cmd sync --no-mime-magic --no-preserve --verbose --add-header='#{gzip_hdr}' --exclude '*' #{gzip_includes} _deploy/ s3://chrisdown.name"
  sh "s3cmd sync --no-mime-magic --no-preserve --delete-removed --verbose --add-header='#{generic_cc}' _deploy/ s3://chrisdown.name"
end

task :set_headers => :sync do
  # gzip header might not be there the very first time, since --add-header in sync will only update new files
  sh "s3cmd modify --recursive --exclude '*' #{gzip_includes} --add-header='#{gzip_hdr}' s3://chrisdown.name"
  sh "s3cmd modify --recursive #{generic_excludes} --add-header='#{generic_cc}' s3://chrisdown.name"
  sh "s3cmd modify --recursive --exclude '*' #{this_week_post_includes} --add-header='#{this_week_post_cc}' s3://chrisdown.name"
  sh "s3cmd modify --recursive --exclude '*' #{static_includes} --add-header='#{static_cc}' s3://chrisdown.name"
  sh "s3cmd modify --add-header='#{enoent_cc}' s3://chrisdown.name/404.html"

  sh "s3cmd modify --recursive --exclude '*' --include '*.html' --add-header='#{html_hdr}' s3://chrisdown.name"
  sh "s3cmd modify --recursive --exclude '*' --include '*.css' --add-header='#{css_hdr}' s3://chrisdown.name"
  sh "s3cmd modify --add-header='#{ta_hdr}' s3://chrisdown.name/.well-known/traffic-advice"
  sh "s3cmd modify --add-header='#{rss_hdr}' s3://chrisdown.name/feed.xml"
end

task :setup_redirects do
  redirects.each do |from, to|
    unless from.end_with?(".html")
      from = "#{from}/index.html"
    end
    sh "s3cmd modify s3://chrisdown.name/#{from} --add-header='x-amz-website-redirect-location:#{to}'"
  end
end

task :deploy => [:create_local_redirects, :sync, :set_headers, :setup_redirects]

task :build => [:build_raw, :check, :gzip]

task :check => :build_raw do
  sh "_checks/tidy"
  # If you don't specify the link for an anchor, Jekyll is a bit funny and
  # lets it go through without fatalling (and sets the link to nothing). We
  # manually check for these to avoid that.
  sh "! grep -R 'href=\"\"' _deploy"
  # Newer versions of the markdown interpreter just put the raw anchor text
  # if you failed to give it a link reference, so we should look for those
  # too.
  sh "! grep -IFR '][]' _deploy/"
end

task :gzip => :build_raw do
  sh "find _deploy/ -type f #{find_names}" + ' -exec gzip -n -9 {} \; -exec mv {}.gz {} \;'
end

task :build_raw do
  sh "JEKYLL_ENV=production jekyll build"
end
