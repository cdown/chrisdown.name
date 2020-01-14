task :default => [:deploy]

expiration_secs = 3600
cc_hdr = "Cache-Control: max-age=#{expiration_secs}, public"

task :deploy => :build do
  sh "s3cmd sync --no-mime-magic --no-preserve --cf-invalidate --delete-removed --verbose --add-header='#{cc_hdr}' _deploy/ s3://chrisdown.name"
end

task :update_cache_control do
  sh "s3cmd modify --recursive --add-header='#{cc_hdr}' s3://chrisdown.name"
end

task :build do
  sh "jekyll build"
end
