task :default => [:deploy]

task :deploy do
  sh "rsync -av --delete deploy/ guthrie:/srv/http/chrisdown.name/"
end
