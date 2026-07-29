<?php
// Gullah Geechee Biz — Code Redemption API
// Called by the redeem page to validate codes and serve downloads

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$input = json_decode(file_get_contents('php://input'), true);
$code = strtoupper(trim($input['code'] ?? ''));

if (!$code || strlen($code) !== 19) {
    echo json_encode(['success' => false, 'error' => 'Invalid code format.']);
    exit;
}

$codes_file = __DIR__ . '/../codes/codes.json';
$ebooks_dir = $_SERVER['HOME'] . '/ebooks/mass/';

if (!file_exists($codes_file)) {
    echo json_encode(['success' => false, 'error' => 'No codes have been issued yet.']);
    exit;
}

$codes = json_decode(file_get_contents($codes_file), true);
$found = null;
$idx = null;

foreach ($codes as $i => $c) {
    if ($c['code'] === $code) {
        $found = $c;
        $idx = $i;
        break;
    }
}

if (!$found) {
    echo json_encode(['success' => false, 'error' => 'Code not found.']);
    exit;
}

if ($found['redeemed']) {
    echo json_encode(['success' => false, 'error' => 'This code has already been redeemed.']);
    exit;
}

// Mark as redeemed
$codes[$idx]['redeemed'] = true;
$codes[$idx]['redeemed_at'] = date('Y-m-d H:i:s');
$codes[$idx]['redeemed_by'] = $input['email'] ?? 'anonymous';
file_put_contents($codes_file, json_encode($codes, JSON_PRETTY_PRINT));

// Find the ebook file
$slug = $found['ebook_slug'];
$ebook_file = $ebooks_dir . $slug . '.docx';

if (!file_exists($ebook_file)) {
    // Try EPUB
    $ebook_file = $ebooks_dir . $slug . '.epub';
}

if (!file_exists($ebook_file)) {
    echo json_encode(['success' => false, 'error' => 'Ebook file not found. Contact support.']);
    exit;
}

// Build title from slug
$title_parts = explode('-', $slug);
$title = ucwords(implode(' ', $title_parts));

echo json_encode([
    'success' => true,
    'title' => $title,
    'download_url' => '/downloads/ebooks/' . $slug . '.docx'
]);
