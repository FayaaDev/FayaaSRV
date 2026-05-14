const INSTALLER_URL = 'https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh'

function responseHeaders(cacheControl) {
  return {
    'Content-Type': 'text/plain; charset=utf-8',
    'Cache-Control': cacheControl,
    'X-Content-Type-Options': 'nosniff',
  }
}

export default {
  async fetch(_request, _env, ctx) {
    const upstreamRequest = new Request(INSTALLER_URL, {
      headers: {
        'User-Agent': 'rakkib-install-proxy',
      },
    })

    let upstream
    try {
      upstream = await fetch(upstreamRequest, {
        cf: {
          cacheTtl: 300,
          cacheEverything: true,
        },
      })
    } catch {
      return new Response('Installer upstream unavailable\n', {
        status: 502,
        headers: responseHeaders('no-store'),
      })
    }

    if (!upstream.ok || !upstream.body) {
      ctx.waitUntil(
        fetch(upstreamRequest, {
          cf: {
            cacheTtl: 0,
            cacheEverything: true,
          },
        }),
      )

      return new Response('Installer upstream unavailable\n', {
        status: 502,
        headers: responseHeaders('no-store'),
      })
    }

    return new Response(upstream.body, {
      status: 200,
      headers: responseHeaders('public, max-age=300'),
    })
  },
}
