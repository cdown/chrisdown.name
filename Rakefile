task :default => [:deploy]

task :deploy => :build do
  sh "s3cmd sync --no-mime-magic --no-preserve --cf-invalidate --delete-removed --verbose --add-header='Cache-Control: max-age=86400, public' _deploy/ s3://chrisdown.name"
end

task :build do
  sh "jekyll build"
end
