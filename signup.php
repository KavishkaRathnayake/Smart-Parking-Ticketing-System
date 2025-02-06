<?php
// Database connection
$servername = "localhost";
$username = "root";  
$password = "";      
$dbname = "ticketing";

$conn = new mysqli($servername, $username, $password, $dbname);

// Check connection
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// Initialize error messages
$email_error = '';
$password_error = '';

// Check if form is submitted
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    $first_name = $conn->real_escape_string($_POST['first_name']);
    $last_name = $conn->real_escape_string($_POST['last_name']);
    $email = $conn->real_escape_string($_POST['email']);
    $mobile_no = $conn->real_escape_string($_POST['mobile_no']);
    $password = $conn->real_escape_string($_POST['password']);
    $confirm_password = $conn->real_escape_string($_POST['confirm_password']);
    $entrance_location = $conn->real_escape_string($_POST['entrance_location']);

    if ($password !== $confirm_password) {
        $password_error = "Passwords do not match!";
    }

    $check_email_query = "SELECT * FROM admin_signup WHERE email = '$email'";
    $result = $conn->query($check_email_query);

    if ($result->num_rows > 0) {
        $email_error = "This email is already registered!";
    } 

    if (empty($email_error) && empty($password_error)) {
        $hashed_password = password_hash($password, PASSWORD_BCRYPT);
        $sql = "INSERT INTO admin_signup (first_name, last_name, email, mobile_no, password, entrance_location) 
                VALUES ('$first_name', '$last_name', '$email', '$mobile_no', '$hashed_password', '$entrance_location')";

        if ($conn->query($sql) === TRUE) {
            header("Location: http://localhost/Vehicle%20Park%20-%20Ticketing%20System/signup_successful.html");
            exit();
        } else {
            echo "Error: " . $conn->error;
        }
    } else {
        header("Location: signup.html?email_error=" . urlencode($email_error) . "&password_error=" . urlencode($password_error));
        exit();
    }
}

$conn->close();
?>
