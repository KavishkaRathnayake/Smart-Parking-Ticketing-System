<?php
session_start();

// Database connection
$servername = "localhost";
$username = "root";  // Your MySQL username
$password = "";      // Your MySQL password (leave blank if using XAMPP with no password set)
$dbname = "user";

$conn = new mysqli($servername, $username, $password, $dbname);

if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// Logout logic
if (isset($_GET['logout'])) {
    session_destroy();
    header("Location: http://localhost/Vehicle%20Park%20-%20Ticketing%20System/login.html");
    exit();
}

// Close connection
$conn->close();
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
    <title>Login Page</title>
</head>
<body class="font-roboto bg-gray-100 flex flex-col items-center min-h-screen justify-center">

<?php if (!isset($_SESSION['user_id'])): ?>
    <!-- Login Form Placeholder -->
    <div class="bg-white p-8 rounded-lg shadow-lg w-96 text-center">
        <h1 class="text-2xl font-bold mb-6">Login</h1>
        <p class="text-gray-600 mb-4">Please log in to continue.</p>
        <a href="http://localhost/Number%20Plate%20System/login.html" class="bg-blue-500 text-white px-4 py-2 rounded-full hover:bg-blue-600 transition">Go to Login Page</a>
    </div>
<?php else: ?>
    <!-- Display Logout Button -->
    <div class="bg-white p-4 rounded-lg shadow-lg w-96 text-center mt-20">
        <h2 class="text-xl mb-4">Welcome!</h2>
        <a href="?logout=true" class="bg-red-500 text-white px-4 py-2 rounded-full hover:bg-red-600 transition">Logout</a>
    </div>
<?php endif; ?>

</body>
</html>
