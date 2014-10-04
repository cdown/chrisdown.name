task :default => [:deploy]

task :deploy => :build do
  sh "s3cmd sync --cf-invalidate --delete-removed --reduced-redundancy --verbose --add-header='Cache-Control: max-age=3600, public' deploy/ s3://chrisdown.name"
end

task :build do
  sh "jekyll build"
end
