<?php
/**
 * The base configuration for WordPress
 *
 * The wp-config.php creation script uses this file during the installation.
 * You don't have to use the website, you can copy this file to "wp-config.php"
 * and fill in the values.
 *
 * This file contains the following configurations:
 *
 * * Database settings
 * * Secret keys
 * * Database table prefix
 * * ABSPATH
 *
 * @link https://developer.wordpress.org/advanced-administration/wordpress/wp-config/
 *
 * @package WordPress
 */

// Load .env file
$envPath = dirname(__DIR__) . '/.env';
if (file_exists($envPath)) {
    $lines = file($envPath, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        if (strpos(trim($line), '#') === 0) continue;
        if (strpos($line, '=') !== false) {
            list($key, $value) = explode('=', $line, 2);
            $key = trim($key);
            $value = trim($value);
            putenv("$key=$value");
            $_ENV[$key] = $value;
            $_SERVER[$key] = $value;
        }
    }
}

// ** Database settings - You can get this info from your web host ** //
/** The name of the database for WordPress */
define( 'DB_NAME',     getenv('WP_DATABASE_NAME') ?: 'wordpress' );

/** Database username */
define( 'DB_USER',     getenv('WP_DATABASE_USERNAME') ?: 'root' );

/** Database password */
define( 'DB_PASSWORD', getenv('WP_DATABASE_PASSWORD') ?: '' );

/** Database hostname */
define( 'DB_HOST',     getenv('DB_HOST') ?: 'db' );

/** Database charset to use in creating database tables. */
define( 'DB_CHARSET', 'utf8mb4' );

/** The database collate type. Don't change this if in doubt. */
define( 'DB_COLLATE', '' );

/**#@+
 * Authentication unique keys and salts.
 *
 * Change these to different unique phrases! You can generate these using
 * the {@link https://api.wordpress.org/secret-key/1.1/salt/ WordPress.org secret-key service}.
 *
 * You can change these at any point in time to invalidate all existing cookies.
 * This will force all users to have to log in again.
 *
 * @since 2.6.0
 */
define( 'AUTH_KEY',         '[&0{AJ+$:x+e>?>@TEWikZ/>:G*eH@TfV;h}2Cc[YIqzrSS(`U6WvI.o4K_30Du1' );
define( 'SECURE_AUTH_KEY',  '& /f)-1wq_#TZtCFRSnVBH%`e?1d_NK,<Fa-FI6J[Jgl|l<V(kMcXk:/HV2LC<a;' );
define( 'LOGGED_IN_KEY',    '#rcT!KJ~n^XLbbVe{R8E6s.Nr+$1B+uBh1H{An[$x_;!/#(9G,ug4)m10iwE,lpR' );
define( 'NONCE_KEY',        '$.LIDHwZ@dq|pW*e2^EX_>c.14t_Z4;is(1e)45j#(p((/Qd2`sTeps+`>*br8aD' );
define( 'AUTH_SALT',        'h|8cSC+NphBv&bNCS5}.D|$ 8TijNkOA/;CH.^_r`QRZ9Q[=95) )N._m9<hWl(T' );
define( 'SECURE_AUTH_SALT', '5@$=C/K}F-LGln=TTu:j;=rw/~4kTwwZCp:qzAtt`A[:TqV57=x6e]8H4+t4%K#O' );
define( 'LOGGED_IN_SALT',   's]Fg/79etf.;Cs=R T[}43Q&tp[dc%K1!XRx@!e:=j/rB#z*(0bcw|L%Sx%=e+5g' );
define( 'NONCE_SALT',       ')b5JjUeRA}n8w@)I!.1QmG-oi#F;9>LfGfDNd)%IBL(1>!#D)X#ApuoAt1ihrb@u' );

/**#@-*/

/**
 * WordPress database table prefix.
 *
 * You can have multiple installations in one database if you give each
 * a unique prefix. Only numbers, letters, and underscores please!
 *
 * At the installation time, database tables are created with the specified prefix.
 * Changing this value after WordPress is installed will make your site think
 * it has not been installed.
 *
 * @link https://developer.wordpress.org/advanced-administration/wordpress/wp-config/#table-prefix
 */
$table_prefix = 'wp_';

/**
 * For developers: WordPress debugging mode.
 *
 * Change this to true to enable the display of notices during development.
 * It is strongly recommended that plugin and theme developers use WP_DEBUG
 * in their development environments.
 *
 * For information on other constants that can be used for debugging,
 * visit the documentation.
 *
 * @link https://developer.wordpress.org/advanced-administration/debug/debug-wordpress/
 */
define( 'WP_DEBUG', false );

/* Add any custom values between this line and the "stop editing" line. */



/* That's all, stop editing! Happy publishing. */

/** Absolute path to the WordPress directory. */
if ( ! defined( 'ABSPATH' ) ) {
	define( 'ABSPATH', __DIR__ . '/' );
}

/** Sets up WordPress vars and included files. */
require_once ABSPATH . 'wp-settings.php';
