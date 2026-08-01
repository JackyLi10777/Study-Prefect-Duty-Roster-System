/*
 * Local workerd-only service binding for the mixed gateway load verifier.
 *
 * This adapter deliberately accepts exactly one loopback HTTP origin. It must
 * never become a production route, tunnel, or generic forward proxy.
 */

function loopbackTarget(rawValue) {
  if (typeof rawValue !== 'string' || rawValue !== rawValue.trim()) {
    throw new Error('LOOPBACK_ORIGIN is missing or malformed');
  }
  const target = new URL(rawValue);
  if (
    target.protocol !== 'http:'
    || target.hostname !== '127.0.0.1'
    || !target.port
    || target.username
    || target.password
    || target.pathname !== '/'
    || target.search
    || target.hash
  ) {
    throw new Error('LOOPBACK_ORIGIN must be an exact 127.0.0.1 HTTP origin');
  }
  const port = Number(target.port);
  if (!Number.isSafeInteger(port) || port < 1024 || port > 65535) {
    throw new Error('LOOPBACK_ORIGIN port is outside the test-only range');
  }
  return target;
}

export default {
  async fetch(request, env) {
    const source = new URL(request.url);
    const target = loopbackTarget(env.LOOPBACK_ORIGIN);
    target.pathname = source.pathname;
    target.search = source.search;

    const headers = new Headers(request.headers);
    headers.delete('Host');
    // workerd may transparently decode a loopback fetch body while retaining
    // the upstream Content-Encoding header. Request identity encoding so the
    // browser receives an unambiguous byte stream through this test adapter.
    headers.set('Accept-Encoding', 'identity');
    const init = {
      method: request.method,
      headers,
      redirect: 'manual',
    };
    if (!['GET', 'HEAD'].includes(request.method.toUpperCase())) {
      init.body = request.body;
    }
    return fetch(new Request(target.toString(), init));
  },
};
