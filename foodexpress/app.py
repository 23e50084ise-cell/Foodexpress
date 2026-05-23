import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pymysql
pymysql.install_as_MySQLdb()

from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)

# ─── Configuración ────────────────────────────────────────────────
# Secret key y credenciales - TODO: se deben configurar en el hosting vía variables de entorno
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-me-in-production')

app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'foodexpress_market')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'


UPLOAD_FOLDER   = os.path.join('static', 'uploads')
ALLOWED_EXT     = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

import pymysql
pymysql.install_as_MySQLdb()
mysql = MySQL(app)
# ──────────────────────────────────────────────────────────────────


# ─── Helpers ──────────────────────────────────────────────────────
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def save_image(file):
    if file and allowed_file(file.filename):
        ext      = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return filename
    return None


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('user_tipo') not in roles:
                flash('No tienes permiso para acceder a esa página.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated
    return decorator
# ──────────────────────────────────────────────────────────────────


# ─── Rutas públicas ───────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' in session:
        tipo = session.get('user_tipo')
        if tipo == 'vendedor':
            return redirect(url_for('vendedor_dashboard'))
        if tipo == 'repartidor':
            return redirect(url_for('repartidor_dashboard'))
        return redirect(url_for('cliente_inicio'))
    return redirect(url_for('login'))


@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre   = request.form['nombre'].strip()
        correo   = request.form['correo'].strip().lower()
        password = request.form['password']
        tipo     = request.form['tipo']

        if not nombre or not correo or not password:
            flash('Todos los campos son obligatorios.', 'danger')
            return redirect(url_for('registro'))

        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM usuarios WHERE correo=%s", (correo,))
        if cur.fetchone():
            flash('Ese correo ya está registrado.', 'danger')
            cur.close()
            return redirect(url_for('registro'))

        hashed = generate_password_hash(password)
        cur.execute(
            "INSERT INTO usuarios (nombre, correo, password, tipo) VALUES (%s,%s,%s,%s)",
            (nombre, correo, hashed, tipo)
        )
        mysql.connection.commit()
        cur.close()
        flash('¡Cuenta creada! Ahora inicia sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('auth/registro.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo   = request.form['correo'].strip().lower()
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM usuarios WHERE correo=%s", (correo,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user['password'], password):
            session['user_id']     = user['id']
            session['user_nombre'] = user['nombre']
            session['user_tipo']   = user['tipo']
            session['carrito']     = session.get('carrito', [])
            return redirect(url_for('index'))

        flash('Correo o contraseña incorrectos.', 'danger')
    return render_template('auth/login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
# ──────────────────────────────────────────────────────────────────


# ─── Panel Cliente ────────────────────────────────────────────────
@app.route('/cliente')
@login_required
@role_required('cliente')
def cliente_inicio():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.*, u.nombre AS vendedor_nombre,
               COUNT(pr.id) AS num_productos
        FROM puestos p
        JOIN usuarios u ON u.id = p.vendedor_id
        LEFT JOIN productos pr ON pr.puesto_id = p.id AND pr.disponible=1
        WHERE p.activo=1
        GROUP BY p.id
    """)
    puestos = cur.fetchall()
    cur.close()
    return render_template('cliente/inicio.html', puestos=puestos)


@app.route('/cliente/puesto/<int:puesto_id>')
@login_required
@role_required('cliente')
def cliente_menu(puesto_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT p.*, u.nombre AS vendedor_nombre FROM puestos p JOIN usuarios u ON u.id=p.vendedor_id WHERE p.id=%s AND p.activo=1", (puesto_id,))
    puesto = cur.fetchone()
    if not puesto:
        flash('Puesto no encontrado.', 'warning')
        return redirect(url_for('cliente_inicio'))
    cur.execute("SELECT * FROM productos WHERE puesto_id=%s AND disponible=1", (puesto_id,))
    productos = cur.fetchall()
    cur.close()
    return render_template('cliente/menu.html', puesto=puesto, productos=productos)


@app.route('/cliente/carrito/agregar', methods=['POST'])
@login_required
@role_required('cliente')
def agregar_carrito():
    data = request.get_json()
    producto_id = int(data['producto_id'])

    cur = mysql.connection.cursor()
    cur.execute("SELECT pr.*, p.id AS puesto_id, p.nombre AS puesto_nombre FROM productos pr JOIN puestos p ON p.id=pr.puesto_id WHERE pr.id=%s", (producto_id,))
    producto = cur.fetchone()
    cur.close()

    if not producto:
        return jsonify({'ok': False})

    carrito = session.get('carrito', [])

    # Verificar que todos los productos sean del mismo puesto
    if carrito and carrito[0]['puesto_id'] != producto['puesto_id']:
        return jsonify({'ok': False, 'msg': 'Solo puedes pedir de un puesto a la vez. Vacía el carrito primero.'})

    # Si ya existe, aumentar cantidad
    for item in carrito:
        if item['producto_id'] == producto_id:
            item['cantidad'] += 1
            session['carrito'] = carrito
            session.modified = True
            return jsonify({'ok': True, 'total': len(carrito)})

    carrito.append({
        'producto_id':   producto['id'],
        'nombre':        producto['nombre'],
        'precio':        float(producto['precio']),
        'imagen':        producto['imagen'],
        'puesto_id':     producto['puesto_id'],
        'puesto_nombre': producto['puesto_nombre'],
        'cantidad':      1,
    })
    session['carrito'] = carrito
    session.modified   = True
    return jsonify({'ok': True, 'total': len(carrito)})


@app.route('/cliente/carrito')
@login_required
@role_required('cliente')
def ver_carrito():
    carrito = session.get('carrito', [])
    total   = sum(i['precio'] * i['cantidad'] for i in carrito)
    return render_template('cliente/carrito.html', carrito=carrito, total=total)


@app.route('/cliente/carrito/eliminar/<int:producto_id>')
@login_required
@role_required('cliente')
def eliminar_carrito(producto_id):
    carrito = session.get('carrito', [])
    carrito = [i for i in carrito if i['producto_id'] != producto_id]
    session['carrito'] = carrito
    session.modified   = True
    return redirect(url_for('ver_carrito'))


@app.route('/cliente/carrito/vaciar')
@login_required
@role_required('cliente')
def vaciar_carrito():
    session['carrito'] = []
    session.modified   = True
    return redirect(url_for('ver_carrito'))


@app.route('/cliente/pedido/confirmar', methods=['POST'])
@login_required
@role_required('cliente')
def confirmar_pedido():
    carrito   = session.get('carrito', [])
    direccion = request.form.get('direccion', '').strip()

    if not carrito:
        flash('Tu carrito está vacío.', 'warning')
        return redirect(url_for('ver_carrito'))
    if not direccion:
        flash('Ingresa una dirección de entrega.', 'warning')
        return redirect(url_for('ver_carrito'))

    total     = sum(i['precio'] * i['cantidad'] for i in carrito)
    puesto_id = carrito[0]['puesto_id']

    cur = mysql.connection.cursor()

    # Buscar repartidor disponible (sin pedidos activos)
    cur.execute("""
        SELECT u.id FROM usuarios u
        WHERE u.tipo='repartidor'
        AND u.id NOT IN (
            SELECT DISTINCT repartidor_id FROM pedidos
            WHERE estado IN ('aceptado','en_camino') AND repartidor_id IS NOT NULL
        )
        LIMIT 1
    """)
    repartidor = cur.fetchone()
    repartidor_id = repartidor['id'] if repartidor else None

    cur.execute(
        "INSERT INTO pedidos (cliente_id, repartidor_id, puesto_id, total, direccion_entrega) VALUES (%s,%s,%s,%s,%s)",
        (session['user_id'], repartidor_id, puesto_id, total, direccion)
    )
    pedido_id = cur.lastrowid

    for item in carrito:
        cur.execute(
            "INSERT INTO detalle_pedido (pedido_id, producto_id, cantidad, precio_unitario) VALUES (%s,%s,%s,%s)",
            (pedido_id, item['producto_id'], item['cantidad'], item['precio'])
        )

    mysql.connection.commit()
    cur.close()

    session['carrito'] = []
    session.modified   = True
    flash(f'¡Pedido #{pedido_id} realizado con éxito!', 'success')
    return redirect(url_for('cliente_pedidos'))


@app.route('/cliente/pedidos')
@login_required
@role_required('cliente')
def cliente_pedidos():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT pe.*, p.nombre AS puesto_nombre, u.nombre AS repartidor_nombre
        FROM pedidos pe
        JOIN puestos p ON p.id=pe.puesto_id
        LEFT JOIN usuarios u ON u.id=pe.repartidor_id
        WHERE pe.cliente_id=%s
        ORDER BY pe.fecha_pedido DESC
    """, (session['user_id'],))
    pedidos = cur.fetchall()
    cur.close()
    return render_template('cliente/pedidos.html', pedidos=pedidos)


@app.route('/cliente/pedido/<int:pedido_id>')
@login_required
@role_required('cliente')
def cliente_detalle_pedido(pedido_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT pe.*, p.nombre AS puesto_nombre, u.nombre AS repartidor_nombre
        FROM pedidos pe
        JOIN puestos p ON p.id=pe.puesto_id
        LEFT JOIN usuarios u ON u.id=pe.repartidor_id
        WHERE pe.id=%s AND pe.cliente_id=%s
    """, (pedido_id, session['user_id']))
    pedido = cur.fetchone()
    if not pedido:
        flash('Pedido no encontrado.', 'warning')
        return redirect(url_for('cliente_pedidos'))
    cur.execute("""
        SELECT dp.*, pr.nombre, pr.imagen
        FROM detalle_pedido dp
        JOIN productos pr ON pr.id=dp.producto_id
        WHERE dp.pedido_id=%s
    """, (pedido_id,))
    detalles = cur.fetchall()
    cur.close()
    return render_template('cliente/detalle_pedido.html', pedido=pedido, detalles=detalles)
# ──────────────────────────────────────────────────────────────────


# ─── Panel Vendedor ───────────────────────────────────────────────
@app.route('/vendedor')
@login_required
@role_required('vendedor')
def vendedor_dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM puestos WHERE vendedor_id=%s", (session['user_id'],))
    puesto = cur.fetchone()
    productos = []
    pedidos   = []
    if puesto:
        cur.execute("SELECT * FROM productos WHERE puesto_id=%s ORDER BY id DESC", (puesto['id'],))
        productos = cur.fetchall()
        cur.execute("""
            SELECT pe.*, u.nombre AS cliente_nombre
            FROM pedidos pe
            JOIN usuarios u ON u.id=pe.cliente_id
            WHERE pe.puesto_id=%s
            ORDER BY pe.fecha_pedido DESC
            LIMIT 10
        """, (puesto['id'],))
        pedidos = cur.fetchall()
    cur.close()
    return render_template('vendedor/dashboard.html', puesto=puesto, productos=productos, pedidos=pedidos)


@app.route('/vendedor/puesto/crear', methods=['GET', 'POST'])
@login_required
@role_required('vendedor')
def vendedor_crear_puesto():
    # Verificar que no tenga ya uno
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM puestos WHERE vendedor_id=%s", (session['user_id'],))
    if cur.fetchone():
        cur.close()
        flash('Ya tienes un puesto registrado.', 'info')
        return redirect(url_for('vendedor_dashboard'))
    cur.close()

    if request.method == 'POST':
        nombre      = request.form['nombre'].strip()
        descripcion = request.form['descripcion'].strip()
        imagen      = save_image(request.files.get('imagen'))

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO puestos (vendedor_id, nombre, descripcion, imagen) VALUES (%s,%s,%s,%s)",
            (session['user_id'], nombre, descripcion, imagen)
        )
        mysql.connection.commit()
        cur.close()
        flash('¡Puesto creado con éxito!', 'success')
        return redirect(url_for('vendedor_dashboard'))

    return render_template('vendedor/crear_puesto.html')


@app.route('/vendedor/puesto/editar', methods=['GET', 'POST'])
@login_required
@role_required('vendedor')
def vendedor_editar_puesto():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM puestos WHERE vendedor_id=%s", (session['user_id'],))
    puesto = cur.fetchone()
    if not puesto:
        cur.close()
        return redirect(url_for('vendedor_crear_puesto'))

    if request.method == 'POST':
        nombre      = request.form['nombre'].strip()
        descripcion = request.form['descripcion'].strip()
        nueva_img   = save_image(request.files.get('imagen'))
        imagen      = nueva_img if nueva_img else puesto['imagen']

        cur.execute(
            "UPDATE puestos SET nombre=%s, descripcion=%s, imagen=%s WHERE id=%s",
            (nombre, descripcion, imagen, puesto['id'])
        )
        mysql.connection.commit()
        cur.close()
        flash('Puesto actualizado.', 'success')
        return redirect(url_for('vendedor_dashboard'))

    cur.close()
    return render_template('vendedor/editar_puesto.html', puesto=puesto)


@app.route('/vendedor/producto/agregar', methods=['GET', 'POST'])
@login_required
@role_required('vendedor')
def vendedor_agregar_producto():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM puestos WHERE vendedor_id=%s", (session['user_id'],))
    puesto = cur.fetchone()
    if not puesto:
        cur.close()
        flash('Primero crea tu puesto.', 'warning')
        return redirect(url_for('vendedor_crear_puesto'))

    if request.method == 'POST':
        nombre      = request.form['nombre'].strip()
        descripcion = request.form['descripcion'].strip()
        precio      = float(request.form['precio'])
        imagen      = save_image(request.files.get('imagen'))

        cur.execute(
            "INSERT INTO productos (puesto_id, nombre, descripcion, precio, imagen) VALUES (%s,%s,%s,%s,%s)",
            (puesto['id'], nombre, descripcion, precio, imagen)
        )
        mysql.connection.commit()
        cur.close()
        flash('Producto agregado.', 'success')
        return redirect(url_for('vendedor_dashboard'))

    cur.close()
    return render_template('vendedor/agregar_producto.html', puesto=puesto)


@app.route('/vendedor/producto/editar/<int:producto_id>', methods=['GET', 'POST'])
@login_required
@role_required('vendedor')
def vendedor_editar_producto(producto_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM puestos WHERE vendedor_id=%s", (session['user_id'],))
    puesto = cur.fetchone()
    cur.execute("SELECT * FROM productos WHERE id=%s AND puesto_id=%s", (producto_id, puesto['id']))
    producto = cur.fetchone()
    if not producto:
        cur.close()
        flash('Producto no encontrado.', 'warning')
        return redirect(url_for('vendedor_dashboard'))

    if request.method == 'POST':
        nombre      = request.form['nombre'].strip()
        descripcion = request.form['descripcion'].strip()
        precio      = float(request.form['precio'])
        disponible  = 1 if request.form.get('disponible') else 0
        nueva_img   = save_image(request.files.get('imagen'))
        imagen      = nueva_img if nueva_img else producto['imagen']

        cur.execute(
            "UPDATE productos SET nombre=%s, descripcion=%s, precio=%s, imagen=%s, disponible=%s WHERE id=%s",
            (nombre, descripcion, precio, imagen, disponible, producto_id)
        )
        mysql.connection.commit()
        cur.close()
        flash('Producto actualizado.', 'success')
        return redirect(url_for('vendedor_dashboard'))

    cur.close()
    return render_template('vendedor/editar_producto.html', producto=producto)


@app.route('/vendedor/producto/eliminar/<int:producto_id>')
@login_required
@role_required('vendedor')
def vendedor_eliminar_producto(producto_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM puestos WHERE vendedor_id=%s", (session['user_id'],))
    puesto = cur.fetchone()
    cur.execute("DELETE FROM productos WHERE id=%s AND puesto_id=%s", (producto_id, puesto['id']))
    mysql.connection.commit()
    cur.close()
    flash('Producto eliminado.', 'info')
    return redirect(url_for('vendedor_dashboard'))
# ──────────────────────────────────────────────────────────────────


# ─── Panel Repartidor ─────────────────────────────────────────────
@app.route('/repartidor')
@login_required
@role_required('repartidor')
def repartidor_dashboard():
    cur = mysql.connection.cursor()
    # Pedidos disponibles (pendientes sin repartidor)
    cur.execute("""
        SELECT pe.*, p.nombre AS puesto_nombre, u.nombre AS cliente_nombre
        FROM pedidos pe
        JOIN puestos p ON p.id=pe.puesto_id
        JOIN usuarios u ON u.id=pe.cliente_id
        WHERE pe.estado='pendiente' AND pe.repartidor_id IS NULL
        ORDER BY pe.fecha_pedido ASC
    """)
    disponibles = cur.fetchall()

    # Mis pedidos activos
    cur.execute("""
        SELECT pe.*, p.nombre AS puesto_nombre, u.nombre AS cliente_nombre
        FROM pedidos pe
        JOIN puestos p ON p.id=pe.puesto_id
        JOIN usuarios u ON u.id=pe.cliente_id
        WHERE pe.repartidor_id=%s AND pe.estado NOT IN ('entregado','cancelado')
        ORDER BY pe.fecha_pedido DESC
    """, (session['user_id'],))
    mis_pedidos = cur.fetchall()

    # Historial
    cur.execute("""
        SELECT pe.*, p.nombre AS puesto_nombre, u.nombre AS cliente_nombre
        FROM pedidos pe
        JOIN puestos p ON p.id=pe.puesto_id
        JOIN usuarios u ON u.id=pe.cliente_id
        WHERE pe.repartidor_id=%s AND pe.estado IN ('entregado','cancelado')
        ORDER BY pe.fecha_pedido DESC
        LIMIT 20
    """, (session['user_id'],))
    historial = cur.fetchall()
    cur.close()

    return render_template('repartidor/dashboard.html',
                           disponibles=disponibles,
                           mis_pedidos=mis_pedidos,
                           historial=historial)


@app.route('/repartidor/aceptar/<int:pedido_id>')
@login_required
@role_required('repartidor')
def repartidor_aceptar(pedido_id):
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE pedidos SET repartidor_id=%s, estado='aceptado' WHERE id=%s AND estado='pendiente' AND repartidor_id IS NULL",
        (session['user_id'], pedido_id)
    )
    mysql.connection.commit()
    cur.close()
    flash(f'Pedido #{pedido_id} aceptado.', 'success')
    return redirect(url_for('repartidor_dashboard'))


@app.route('/repartidor/estado/<int:pedido_id>/<estado>')
@login_required
@role_required('repartidor')
def repartidor_cambiar_estado(pedido_id, estado):
    estados_validos = ['en_camino', 'entregado', 'cancelado']
    if estado not in estados_validos:
        flash('Estado inválido.', 'danger')
        return redirect(url_for('repartidor_dashboard'))
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE pedidos SET estado=%s WHERE id=%s AND repartidor_id=%s",
        (estado, pedido_id, session['user_id'])
    )
    mysql.connection.commit()
    cur.close()
    flash(f'Estado actualizado a: {estado.replace("_"," ").title()}', 'success')
    return redirect(url_for('repartidor_dashboard'))
# ──────────────────────────────────────────────────────────────────


if __name__ == '__main__':
    # Solo ejecución local (debug). En hosting usa WSGI (gunicorn/wsgi:app).
    app.run(debug=True)

