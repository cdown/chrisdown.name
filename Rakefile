task :default => [:deploy]

task :deploy => :build do
  sh "s3cmd sync --delete-removed --reduced-redundancy --verbose deploy/ s3://chrisdown.name"
end

task :build do
  sh "jekyll build"
end
