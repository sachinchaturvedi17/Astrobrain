<?php
/**
 * AstroNaradMuni v1.4.0 — Hostinger Business Web Hosting Gateway (public_html/api_gateway.php)
 *
 * How it works on Hostinger Business Web Hosting:
 * 1. Connects your Python backend to your local Hostinger MySQL database (127.0.0.1:3306).
 * 2. Keeps a fast local Python worker alive on 127.0.0.1:18000 inside your Hostinger container
 *    (auto-restarting it in the background if CloudLinux ever recycles idle processes).
 * 3. If background sockets are unavailable, automatically falls back to direct CLI execution
 *    via cgi_dispatch.py so every /api/v10/* and PDF download request always succeeds.
 */

// --- 1. Configure your Hostinger hPanel MySQL credentials here (from hPanel -> Websites -> Databases) ---
$MYSQL_HOST     = getenv('MYSQL_HOST')     ?: '127.0.0.1';
$MYSQL_PORT     = getenv('MYSQL_PORT')     ?: '3306';
$MYSQL_DATABASE = getenv('MYSQL_DATABASE') ?: 'u123456789_astrodb';   // <-- Replace with your hPanel DB name
$MYSQL_USER     = getenv('MYSQL_USER')     ?: 'u123456789_astro';     // <-- Replace with your hPanel DB user
$MYSQL_PASSWORD = getenv('MYSQL_PASSWORD') ?: 'REPLACE_WITH_DB_PASS'; // <-- Replace with your hPanel DB password
$ADMIN_KEY      = getenv('ASTROMUNI_ADMIN_KEY') ?: '';                // Optional secret for /api/v10/admin/users

// Paths inside your Hostinger Business SSH home directory (/home/uXXXXXXXXX/)
$HOME_DIR   = getenv('HOME') ?: dirname(dirname(__DIR__));
$APP_DIR    = $HOME_DIR . '/Astrobrain';
$PYTHON_BIN = $HOME_DIR . '/astro_venv/bin/python3';
$LOCAL_PORT = 18000;

putenv("MYSQL_HOST={$MYSQL_HOST}");
putenv("MYSQL_PORT={$MYSQL_PORT}");
putenv("MYSQL_DATABASE={$MYSQL_DATABASE}");
putenv("MYSQL_USER={$MYSQL_USER}");
putenv("MYSQL_PASSWORD={$MYSQL_PASSWORD}");
if ($ADMIN_KEY !== '') {
    putenv("ASTROMUNI_ADMIN_KEY={$ADMIN_KEY}");
}

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$uri    = $_SERVER['REQUEST_URI'] ?? '/';
$parts  = explode('?', $uri, 2);
$path   = $parts[0];
$query  = $parts[1] ?? ($_SERVER['QUERY_STRING'] ?? '');
$rawBody = file_get_contents('php://input') ?: '';

/**
 * Check if the local Python worker is listening on 127.0.0.1:18000; if not, spawn it.
 */
function ensure_python_worker(string $pythonBin, string $appDir, int $port): bool {
    $fp = @fsockopen('127.0.0.1', $port, $errno, $errstr, 0.15);
    if ($fp) {
        fclose($fp);
        return true;
    }
    if (!is_executable($pythonBin) || !is_file($appDir . '/run_server.py')) {
        return false;
    }
    $cmd = sprintf(
        'cd %s && nohup %s run_server.py --host 127.0.0.1 --port %d > %s/astromuni_worker.log 2>&1 &',
        escapeshellarg($appDir),
        escapeshellarg($pythonBin),
        $port,
        escapeshellarg($appDir)
    );
    @exec($cmd);
    for ($i = 0; $i < 12; $i++) {
        usleep(150000); // 150ms
        $fp = @fsockopen('127.0.0.1', $port, $errno, $errstr, 0.15);
        if ($fp) {
            fclose($fp);
            return true;
        }
    }
    return false;
}

// --- 2. Fast Path: Proxy to local persistent Python worker on 127.0.0.1:18000 ---
if (ensure_python_worker($PYTHON_BIN, $APP_DIR, $LOCAL_PORT) && function_exists('curl_init')) {
    $targetUrl = "http://127.0.0.1:{$LOCAL_PORT}{$path}" . ($query !== '' ? "?{$query}" : '');
    $ch = curl_init($targetUrl);
    curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HEADER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 25);
    if ($method === 'POST') {
        curl_setopt($ch, CURLOPT_POSTFIELDS, $rawBody);
        curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    }
    $resp = curl_exec($ch);
    if ($resp !== false) {
        $status   = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $hdrSize  = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
        $rawHdrs  = substr($resp, 0, $hdrSize);
        $respBody = substr($resp, $hdrSize);
        curl_close($ch);

        http_response_code($status ?: 200);
        foreach (explode("\r\n", $rawHdrs) as $line) {
            if (stripos($line, 'Content-Type:') === 0 ||
                stripos($line, 'Content-Disposition:') === 0 ||
                stripos($line, 'Cache-Control:') === 0) {
                header($line);
            }
        }
        echo $respBody;
        exit;
    }
    curl_close($ch);
}

// --- 3. Fallback Path: Direct CLI execution via cgi_dispatch.py ---
$dispatchScript = $APP_DIR . '/deploy/hostinger_business/cgi_dispatch.py';
$cmd = sprintf(
    '%s %s %s %s %s',
    escapeshellarg($PYTHON_BIN),
    escapeshellarg($dispatchScript),
    escapeshellarg($method),
    escapeshellarg($path),
    escapeshellarg($query)
);
$descriptors = [
    0 => ['pipe', 'r'],
    1 => ['pipe', 'w'],
    2 => ['pipe', 'w'],
];
$proc = proc_open($cmd, $descriptors, $pipes, $APP_DIR);
if (!is_resource($proc)) {
    http_response_code(500);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['error' => 'Failed to start Python runtime']);
    exit;
}
fwrite($pipes[0], $rawBody);
fclose($pipes[0]);
$stdout = stream_get_contents($pipes[1]);
fclose($pipes[1]);
$stderr = stream_get_contents($pipes[2]);
fclose($pipes[2]);
proc_close($proc);

$env = json_decode($stdout, true);
if (!is_array($env) || !isset($env['body_b64'])) {
    http_response_code(500);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['error' => 'Invalid response from Python dispatcher', 'detail' => substr($stderr, 0, 200)]);
    exit;
}
http_response_code((int)($env['status'] ?? 200));
header('Content-Type: ' . ($env['content_type'] ?? 'application/json; charset=utf-8'));
if (!empty($env['headers']) && is_array($env['headers'])) {
    foreach ($env['headers'] as $hk => $hv) {
        header("{$hk}: {$hv}");
    }
}
echo base64_decode($env['body_b64']);
