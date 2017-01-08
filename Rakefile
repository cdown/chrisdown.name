task :default => [:deploy]

task :deploy => :build do
  sh "rsync -av -c --delete _deploy/ chrisdown.name:/srv/http/chrisdown.name"
end

task :build do
  sh "jekyll build"
end
