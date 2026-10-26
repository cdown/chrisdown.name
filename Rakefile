require 'json'
require 'fileutils'

task :default => [:deploy]

redirects = JSON.parse(File.read('redirects.json'))

task :create_local_redirects => :build do
  # Reject unsafe redirect sources before writing any stubs.
  redirects.each do |from, to|
    if from.start_with?('/') || from.include?('\\') || from.split('/', -1).any? { |part| ['', '.', '..'].include?(part) }
      raise "Invalid redirect source: #{from}"
    end
    if to.include?("\r") || to.include?("\n")
      raise "Invalid redirect target: #{to}"
    end
  end
  redirects.each do |from, to|
    loc = "_deploy/" + from
    if File.exist?(loc)
      raise "Redirect stub would overwrite #{loc}"
    end

    unless to.start_with?("http://", "https://")
      unless File.file?(Dir.pwd + "/_deploy/" + to)
        raise "Missing redirect target to #{to}"
      end
    end

    if File.extname(loc).empty?
      FileUtils.mkdir_p(loc)
      File.open("#{loc}/index.html", "w") {}
    else
      # Old redirects that used to be handled by jekyll-redirect-from
      FileUtils.mkdir_p(File.dirname(loc))
      File.open(loc, "w") {}
    end
  end
end

task :sync => :create_local_redirects do
  sh 'python3', '_scripts/deploy.py'
end

task :deploy => :sync

desc "Preview content and metadata changes without writing to S3"
task :deploy_dry_run => :create_local_redirects do
  sh 'python3', '_scripts/deploy.py', '--dry-run'
end

desc "Test deployment reconciliation and edge cases without AWS access"
task :check_deploy do
  sh 'python3', '-m', 'unittest', 'discover', '-s', '_checks', '-p', 'test_deploy.py', '-v'
end

task :build => [:build_raw, :check]

task :check => :build_raw do
  sh "_checks/tidy"
  # If you don't specify the link for an anchor, Jekyll is a bit funny and
  # lets it go through without fatalling (and sets the link to nothing). We
  # manually check for these to avoid that.
  sh "! grep -R 'href=\"\"' _deploy"
  # Newer versions of the markdown interpreter just put the raw anchor text
  # if you failed to give it a link reference, so we should look for those
  # too.
  sh "! grep -IFR '][]' _deploy/"
end

desc "Check compression negotiation on the live site"
task :check_compression do
  sh "_checks/compression"
end

task :build_raw do
  # Postprocessors change copied static HTML too. Do not let Jekyll reuse that
  # output as input on the next build; retain .jekyll-cache for costly renders.
  FileUtils.rm_rf('_deploy')
  sh "JEKYLL_ENV=production jekyll build"
  sh 'python3', '_scripts/optimise_media.py'
  sh 'python3', '_scripts/fingerprint.py'
end
