task :default => [:deploy]

task :build => [:build_raw, :gzip]

task :deploy => :build do
  sh "s3cmd sync --no-mime-magic --no-preserve --cf-invalidate --delete-removed --reduced-redundancy --verbose --add-header='Content-Encoding: gzip' --add-header='Cache-Control: max-age=86400, public' _deploy/ s3://chrisdown.name"
  sh "s3cmd modify --cf-invalidate --recursive --exclude '*' --include '*.jpg' --include '*.png' --include '*.mp4' --remove-header='Content-Encoding' s3://chrisdown.name"
end

task :gzip => :build_raw do
  sh 'find _deploy/ -type f -not -name "*.jpg" -not -name "*.mp4" -not -name "*.png" -exec gzip -n -9 {} \; -exec mv {}.gz {} \;'
end

task :build_raw do
  sh "jekyll build"
end
