task :default => [:deploy]

expiration_secs = 86400
cc_hdr = "Cache-Control: max-age=#{expiration_secs}, public"


task :build => [:build_raw, :gzip]

task :deploy => :build do
  sh "s3cmd sync --no-mime-magic --no-preserve --delete-removed --verbose --add-header='#{cc_hdr}' _deploy/ s3://chrisdown.name"
  sh "s3cmd modify --recursive --exclude '*.jpg' --exclude '*.png' --exclude '*.mp4' --add-header='Content-Encoding: gzip' s3://chrisdown.name"
  sh "aws cloudfront create-invalidation --distribution-id=E3JFDQ2QEF0HR7 --paths /"
  sh "aws cloudfront create-invalidation --distribution-id=E3PXQXBK6DFKDU --paths /"
end

task :gzip => :build_raw do
  sh 'find _deploy/ -type f -not -name "*.jpg" -not -name "*.mp4" -not -name "*.png" -exec gzip -n -9 {} \; -exec mv {}.gz {} \;'
end

task :build_raw do
  sh "jekyll build"
end
