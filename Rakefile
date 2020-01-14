require 'date'

task :default => [:deploy]

cc_hdr = "Cache-Control: public, max-age=%d, must-revalidate"

# 1 hour for anything unspecified
generic_cc = cc_hdr % (60 * 60)
generic_excludes = ""

# 5 minutes for posts written in the last 7 days, as updates may be more
# frequent
this_week_post_cc = cc_hdr % (5 * 60)
this_week_post_includes = ""
(Date.today-6..Date.today).map do |date|
  date_glob = date.strftime("%Y/%m/%d") + "/*"
  this_week_post_includes += " --include '#{date_glob}' "
  generic_excludes += " --exclude '#{date_glob}' "
end

# Cache 404s for 2 minutes, since if something is broken we want to fix it
# fast, but a mass storm to S3 backend should still be avoided
enoent_cc = cc_hdr % (2 * 60)
generic_excludes += " --exclude 404.html "

task :deploy => :build do
  sh "s3cmd sync --no-mime-magic --no-preserve --cf-invalidate --delete-removed --verbose --add-header='#{cc_hdr}' _deploy/ s3://chrisdown.name"
end

task :update_cache_control do
  sh "s3cmd modify --recursive #{generic_excludes} --add-header='#{generic_cc}' s3://chrisdown.name"
  sh "s3cmd modify --recursive --exclude '*' #{this_week_post_includes} --add-header='#{this_week_post_cc}' s3://chrisdown.name"
  sh "s3cmd modify --add-header='#{enoent_cc}' s3://chrisdown.name/404.html"
end

task :build do
  sh "jekyll build"
end
