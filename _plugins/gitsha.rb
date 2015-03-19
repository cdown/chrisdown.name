module Jekyll
  class GitSHAGenerator < Generator
    priority :low
    safe false

    def generate(site)
      site.data['git_sha'] = %x(git rev-parse --short HEAD).strip
    end
  end
end
