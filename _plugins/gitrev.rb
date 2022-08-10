module GitRevPlugin
  class GitRev < Jekyll::Generator
    safe true
    def generate(site)
      site.data['gitrev'] = %x(git rev-parse --short HEAD).strip
    end
  end
end
