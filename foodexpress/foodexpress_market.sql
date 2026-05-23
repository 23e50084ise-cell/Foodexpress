DROP DATABASE foodexpress_market;
SHOW DATABASES;
-- 1. Crear la base de datos
CREATE DATABASE IF NOT EXISTS foodexpress_market;
USE foodexpress_market;

-- 2. Tabla de Usuarios (Maneja Clientes, Vendedores y Repartidores)
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    correo VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL, -- Para los hashes de Werkzeug
    tipo ENUM('cliente', 'vendedor', 'repartidor') NOT NULL
);

-- 3. Tabla de Puestos (Locales de los vendedores)
CREATE TABLE IF NOT EXISTS puestos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vendedor_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    imagen VARCHAR(255),
    activo TINYINT(1) DEFAULT 1, -- ¡Esta es la que causaba el error!
    FOREIGN KEY (vendedor_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- 4. Tabla de Productos
CREATE TABLE IF NOT EXISTS productos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    puesto_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(10, 2) NOT NULL,
    imagen VARCHAR(255),
    disponible TINYINT(1) DEFAULT 1,
    FOREIGN KEY (puesto_id) REFERENCES puestos(id) ON DELETE CASCADE
);

-- 5. Tabla de Pedidos
CREATE TABLE IF NOT EXISTS pedidos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT NOT NULL,
    repartidor_id INT DEFAULT NULL,
    puesto_id INT NOT NULL,
    total DECIMAL(10, 2) NOT NULL,
    direccion_entrega TEXT NOT NULL,
    estado ENUM('pendiente', 'aceptado', 'en_camino', 'entregado', 'cancelado') DEFAULT 'pendiente',
    fecha_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES usuarios(id),
    FOREIGN KEY (repartidor_id) REFERENCES usuarios(id),
    FOREIGN KEY (puesto_id) REFERENCES puestos(id)
);

-- 6. Tabla de Detalle de Pedidos (Los productos dentro de cada pedido)
CREATE TABLE IF NOT EXISTS detalle_pedido (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pedido_id INT NOT NULL,
    producto_id INT NOT NULL,
    cantidad INT NOT NULL,
    precio_unitario DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);