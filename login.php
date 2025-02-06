<?php
// Database connection
$servername = "localhost";
$username = "root";  // Your MySQL username
$password = "";      // Your MySQL password (leave blank if using XAMPP with no password set)
$dbname = "ticketing";

// Create connection
$conn = new mysqli($servername, $username, $password, $dbname);

// Check connection
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// Check if form is submitted
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    // Retrieve and sanitize form inputs
    $admin_id = $conn->real_escape_string($_POST['admin_id']);
    $password = $conn->real_escape_string($_POST['password']);

    // Query to find the admin by Admin ID
    $sql = "SELECT * FROM admin_signup WHERE email='$admin_id'"; // Assuming Admin ID is the email
    $result = $conn->query($sql);

    if ($result->num_rows > 0) {
        // Fetch the admin data
        $admin = $result->fetch_assoc();

        // Verify the password
        if (password_verify($password, $admin['password'])) {
            // Password is correct
            echo "Login successful!";
            // Redirect to admin dashboard
            header("Location: http://localhost/Vehicle%20Park%20-%20Ticketing%20System/dashboard.html");
            exit; // Ensure no further code is executed after redirect
        } else {
            // Invalid password
            echo "Invalid password!";
        }
    } else {
        // Admin ID not found
        echo "Admin ID not found!";
    }

    // Close the connection
    $conn->close();
}
?>
