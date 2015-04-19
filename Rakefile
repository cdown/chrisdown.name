task :default => [:deploy]

task :build => [:build_raw, :minify, :gzip]

task :deploy => :build do
  sh "s3cmd sync --exclude '*' --include '*.css' --include '*.js' --include '*.png' --include '*.jpg' --include '*.ico' --no-preserve --cf-invalidate --verbose --add-header='Expires: Wed, 1 Jan 2020 00:00:00 GMT' --add-header='Cache-Control: max-age=6048000, public' --add-header='Content-Encoding: gzip' _deploy/ s3://chrisdown.name"
  sh "s3cmd sync --delete-removed --no-preserve --cf-invalidate --verbose --add-header='Cache-Control: max-age=7200, must-revalidate' --add-header='Content-Encoding: gzip' _deploy/ s3://chrisdown.name"
end

task :gzip => :build_raw do
  sh 'find _deploy/ -type f -exec gzip -n -9 {} \; -exec mv {}.gz {} \;'
end

task :minify => :build_raw do
  sh 'find _deploy/ -type f -name "*.html" -exec sh -c "htmlmin -c -s > /tmp/q < \"\$0\"" {} \; -exec mv /tmp/q {} \;'
end

task :build_raw do
  sh "jekyll build"
end
