from module.database import execute

def init_db():
    sql = """
        CREATE TABLE IF NOT EXISTS users (
            user_id VARCHAR(255) PRIMARY KEY NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            user_email VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            status ENUM('ACTIVE', 'INACTIVE', 'BANNED') NOT NULL DEFAULT 'ACTIVE'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    execute(sql)

    sql = """
        CREATE TABLE IF NOT EXISTS payment_cards (
            card_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,

            -- VISA, MASTERCARD 등
            brand VARCHAR(50) NOT NULL,          
            card_number CHAR(16) NOT NULL, 
            exp_month TINYINT UNSIGNED NOT NULL,
            exp_year SMALLINT UNSIGNED NOT NULL,

            -- 기본 결제카드 여부 / 상태
            is_default TINYINT(1) NOT NULL DEFAULT 0,
            status ENUM('ACTIVE','INACTIVE') NOT NULL DEFAULT 'ACTIVE',

            -- 카드 소유자명
            holder_name VARCHAR(100) NULL,

            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

            KEY idx_user (user_id),
            KEY idx_user_default (user_id, is_default),

            CONSTRAINT fk_payment_cards_user
                FOREIGN KEY (user_id) REFERENCES users(user_id)
                ON DELETE CASCADE
                ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    execute(sql)

    sql = """
        CREATE TABLE IF NOT EXISTS videos (
            video_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            user_id VARCHAR(255) NOT NULL,
            file_path VARCHAR(1024) NOT NULL,
            task_id VARCHAR(255) NOT NULL,
            region VARCHAR(255) NOT NULL,
            recorded_at DATETIME NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status ENUM('PROCESSING', 'COMPLETED', 'FAIL', 'DELETED') NOT NULL DEFAULT 'PROCESSING',

            PRIMARY KEY (video_id),
            KEY idx_videos_user_created (user_id, created_at),
            CONSTRAINT fk_videos_user FOREIGN KEY (user_id) REFERENCES users(user_id)
            ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    execute(sql)

    sql = """
        CREATE TABLE IF NOT EXISTS vehicle_counts (
            vehicle_count_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            video_id BIGINT UNSIGNED NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            total_forward INT NOT NULL DEFAULT 0,
            total_backward INT NOT NULL DEFAULT 0,
            per_class_forward JSON NULL,
            per_class_backward JSON NULL,
            line_a_x INT NULL,
            line_a_y INT NULL,
            line_b_x INT NULL,
            line_b_y INT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        
            PRIMARY KEY (vehicle_count_id),
            KEY idx_vehicle_counts_video (video_id),
            CONSTRAINT fk_vehicle_counts_video FOREIGN KEY (video_id)
            REFERENCES videos(video_id) ON DELETE CASCADE ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    execute(sql)