task :default => [:deploy]

task :deploy => [:build, :gzip] do
  sh "s3cmd sync --no-preserve --cf-invalidate --delete-removed --reduced-redundancy --verbose --add-header='Cache-Control: max-age=86400, public' --add-header='Content-Encoding: gzip' _deploy/ s3://chrisdown.name"
end

task :gzip => :build do
  sh 'find _deploy/ -type f -exec gzip -n -9 {} \; -exec mv {}.gz {} \;'
end

task :build do
  sh "jekyll build"
end
