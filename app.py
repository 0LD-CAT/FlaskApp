from flask import Flask, render_template, url_for, request, redirect, flash, session
import psycopg2
from psycopg2 import Error
from flask_login import LoginManager, login_required, UserMixin
import random

app = Flask(__name__)
app.secret_key = 'qwerty1234'  # Необходимо для работы flash-сообщений


def db_connection():
    try:
        connection = psycopg2.connect(user="postgres",
                                        password="1234",
                                        host="localhost",
                                        port="5432",
                                        database="AppAvtoDetali")
    except (Exception, Error) as error:
        connection = error
        print("Ошибка при работе с PostgreSQL", error)
    return connection


class Product:
    def __init__(self, part_id, part_name, country_prod, producer, price, brand_name, model_name, year):
        self.part_id = part_id
        self.part_name = part_name
        self.country_prod = country_prod
        self.producer = producer
        self.price = price
        self.brand_name = brand_name
        self.model_name = model_name
        self.year = year

def get_products(part_name):
    conn = db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM parts WHERE part_name = %s', (part_name,))
    part_data = cur.fetchall()
    cur.close()
    conn.close()

    return [Product(*data) for data in part_data] if part_data else None


def track_num_gen():
    num = random.randrange(100000000, 999999999)
    return ("TRK" + str(num))


@app.route('/')
def main_page():
    return render_template('main.html')


@app.route('/about')
def about_page():
    return render_template('about.html')


@app.route('/login', methods=['POST', 'GET'])
def login_page():
    if request.method == 'POST':
        phone = request.form['phone']
        code = request.form['code']
        conn = db_connection()
        cur = conn.cursor()
        cur.execute("SELECT EXISTS(SELECT 1 FROM clients WHERE phone_number = %s)", (phone,))
        success = cur.fetchone()[0]
        # Проверка логина и пароля
        if success and code == '1234':
            cur.execute("SELECT * FROM clients WHERE phone_number = %s", (phone, ))
            data_about_client = cur.fetchall()[0]
            cur.close()
            conn.close()
            return redirect('/')
        else:
            flash('Неверный телефон или код!', category='error')
    return render_template('login.html')


def check_num(phone):
    if len(phone) > 0:
        if (phone[0] == '8') and (len(phone) == 11) and (phone.isdigit()):
            return True
        else:
            return False
    else:
        return False

@app.route('/reg', methods=['POST', 'GET'])
def reg_page():
    if request.method == 'POST':
        name = request.form['fio']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        # Проверка пароля
        if check_num(str(phone)):
            conn = db_connection()
            cur = conn.cursor()
            cur.execute("SELECT EXISTS(SELECT 1 FROM clients WHERE phone_number = %s)", (phone,))
            check_phoneNum = cur.fetchone()[0]
            if not check_phoneNum:
                cur.execute("INSERT INTO clients (full_name, phone_number, email, delivery_address, client_status, status_level) VALUES (%s, %s, %s, %s, %s, %s)",
                (str(name), str(phone), str(email), str(address), 'Обычный', 'Стандарт'))
                conn.commit()
                print(f'Регистрация пользователя с номером {phone} прошла успешно!')
                cur.close()
                conn.close()
                return redirect('/login')
            else:
                flash('Этот номер телефона уже зарегистрирован!', 'error')
        else:
            flash('Неправильно введены данные!', 'error')
    return render_template('reg.html')


@app.route('/catalog', methods=['POST', 'GET'])
def catalog_page():
    if 'total_cost' not in session:
        session['total_cost'] = 0
    return render_template('catalog.html', total_cost=session['total_cost'])


def get_all_brands():
    conn = db_connection()
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT brand_name FROM parts ORDER BY brand_name ASC;')
    brands_data = cur.fetchall()
    cur.close()
    conn.close()
    return [item for sublist in brands_data for item in sublist]

def get_all_models():
    conn = db_connection()
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT model_name FROM parts ORDER BY model_name ASC;')
    models_data = cur.fetchall()
    cur.close()
    conn.close()
    return [item for sublist in models_data for item in sublist]

def get_all_years():
    conn = db_connection()
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT year FROM parts ORDER BY year ASC;')
    years_data = cur.fetchall()
    cur.close()
    conn.close()
    return [item for sublist in years_data for item in sublist]

def get_all_providers():
    conn = db_connection()
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT provider_name FROM providers ORDER BY provider_name ASC;')
    providers_data = cur.fetchall()
    cur.close()
    conn.close()
    return [item for sublist in providers_data for item in sublist]

@app.route('/catalog/<string:part_name>', methods=['POST', 'GET'])
def part_page(part_name):
    products = get_products(part_name)
    brands = get_all_brands()
    models = get_all_models()
    years = get_all_years()

    if 'cart' not in session:
        session['cart'] = []  # Инициализация корзины
    if 'total_cost' not in session:
        session['total_cost'] = 0

    # Обработка фильтров
    brand_name = request.args.get('brand_name')
    model_name = request.args.get('model_name')
    year = request.args.get('year')

    if brand_name:
        products = [product for product in products if product.brand_name == brand_name]
    elif model_name:
        products = [product for product in products if product.model_name == model_name]
    elif year:
        products = [product for product in products if str(product.year) == year]

    if not products:
        return "Товар не найден", 404

    # Обработка добавления в корзину
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        part_name = request.form.get('part_name')
        brand_name = request.form.get('brand_name')
        model_name = request.form.get('model_name')
        year = request.form.get('year')
        quantity = int(request.form.get('quantity', 1))
        price = float(request.form.get('price'))

        session['cart'].append({
            'product_id': product_id,
            'part_name': part_name,
            'brand_name': brand_name,
            'model_name': model_name,
            'year': year,
            'quantity': quantity,
            'price': price
        })
        session['total_cost'] += price * quantity

    total_cost = session['total_cost']

    return render_template('product_detail.html', products=products, brands=brands, models=models, years=years, total_cost=total_cost)


def get_product_price(part_id):
    conn = db_connection()
    cur = conn.cursor()
    cur.execute('SELECT price FROM parts where part_id = %s;', (part_id,))
    price_data = cur.fetchall()
    print(price_data)
    cur.close()
    conn.close()
    return price_data

def get_product_by_id(part_id):
    conn = db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM parts where part_id = %s;', (part_id,))
    part_data = cur.fetchall()
    print(part_data)
    cur.close()
    conn.close()
    return part_data


def create_order(order_comment, pay_method, track_num):
    conn = db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO orders (order_status, order_comments, pay_method, pay_date, delivery_track_num) VALUES (%s, %s, %s, %s, %s) RETURNING order_id",
        ('В обработке', str(order_comment), str(pay_method), '2025-01-19', str(track_num)))
    # Получаем order_id
    order_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return order_id  # Возвращаем order_id

def create_orderer_parts(order_id, provider_id, part_id, num_details):
    conn = db_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO num_ordered_parts (order_id, provider_id, part_id, num_details) VALUES (%s, %s, %s, %s)",
        (int(order_id), int(provider_id), int(part_id), int(num_details)))
    conn.commit()
    cur.close()
    conn.close()


@app.route('/submit_order', methods=['POST', 'GET'])
def submit_order():
    supplier = request.form['supplier']
    delivery = request.form['delivery']
    payment = request.form['payment']

    # Получаем детали заказа из скрытых полей
    items = request.form.getlist('items[]')
    # Проверяем общую стоимость
    total_cost = sum(float(item.split('_')[-1]) * int(item.split('_')[-2]) for item in items)

    if total_cost <= 0:
        print()
        return redirect(url_for('catalog_page'))  # Перенаправляем обратно
    # Сохраняем заказ в массив
    order_details = {
        'supplier': supplier,
        'delivery': delivery,
        'payment': payment,
        'items': items
    }

    order = list(order_details.values())
    provider = order[0]
    order_comment = order[1]
    pay_method = order[2]
    track_num = track_num_gen()
    order_id = create_order(order_comment, pay_method, track_num)

    processed_items = []
    for item in items:
        parts = item.split('_')

        # Создаем словарь для каждого товара
        product_info = {
            'part_name': parts[0],
            'brand_name': parts[1],
            'model_name': parts[2],
            'year': parts[3],
            'quantity': int(parts[4]),
            'price': float(parts[5])
        }
        # Добавляем словарь в список обработанных товаров
        processed_items.append(product_info)
    conn = db_connection()
    cur = conn.cursor()
    part_ids = []
    quantities = []
    for part in processed_items:
        quantities.append(part['quantity'])
    # Запрос для получения id деталей
    for part in processed_items:
        cur.execute("SELECT part_id FROM parts WHERE part_name = %s AND brand_name = %s AND model_name = %s AND year = %s", (part['part_name'], part['brand_name'], part['model_name'], part['year']))
        result = cur.fetchone()
        if result:
            part_ids.append(result[0])  # Добавляем id в список
    cur.execute("SELECT provider_id FROM providers WHERE provider_name = %s", (str(provider),))
    result_prov = cur.fetchone()
    cur.close()
    conn.close()
    for i in range(len(part_ids)):
        create_orderer_parts(order_id, int(result_prov[0]), part_ids[i], quantities[i])
    return "Заказ оформлен успешно!", 200


@app.route('/cart', methods=['GET'])
def cart():
    cart_items = session.get('cart', [])
    total_cost = sum(item['price'] * item['quantity'] for item in cart_items)
    providers = get_all_providers()

    return render_template('cart.html', cart_items=cart_items, total_cost=total_cost, providers=providers)


@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    session.pop('cart', None)
    session['total_cost'] = 0
    return redirect(request.referrer)  # Возврат на предыдущую страницу

@app.route('/admin/authorization', methods=['POST', 'GET'])
def admin_auth_page():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Проверка логина и пароля
        if username == 'admin' and password == 'admin':
            return redirect('/admin')
        else:
            return render_template('admin_auth.html')
    return render_template('admin_auth.html')


@app.route('/admin', methods=['POST', 'GET'])
def admin_page():
    clients_data = []
    discounts_data = []
    clients_orders_data = []
    delivery_info_data = []
    num_ordered_parts_data = []
    orders_data = []
    parts_data = []
    providers_data = []
    if request.method == 'POST':
        table_name = request.form.get('table_name')
        if table_name == 'clients':
            conn = db_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM clients ORDER BY client_id;')
            clients_data = cur.fetchall()
            cur.close()
            conn.close()
        elif table_name == 'discounts':
            conn = db_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM discounts')
            discounts_data = cur.fetchall()
            cur.close()
            conn.close()
        elif table_name == 'clients_orders':
            conn = db_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM clients_orders ORDER BY order_id;')
            clients_orders_data = cur.fetchall()
            cur.close()
            conn.close()
        elif table_name == 'delivery_info':
            conn = db_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM delivery_info')
            delivery_info_data = cur.fetchall()
            cur.close()
            conn.close()
        elif table_name == 'num_ordered_parts':
            conn = db_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM num_ordered_parts ORDER BY order_id;')
            num_ordered_parts_data = cur.fetchall()
            cur.close()
            conn.close()
        elif table_name == 'orders':
            conn = db_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM orders ORDER BY order_id;')
            orders_data = cur.fetchall()
            cur.close()
            conn.close()
        elif table_name == 'parts':
            conn = db_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM parts ORDER BY part_id;')
            parts_data = cur.fetchall()
            cur.close()
            conn.close()
        elif table_name == 'providers':
            conn = db_connection()
            cur = conn.cursor()
            cur.execute('SELECT * FROM providers ORDER BY provider_id;')
            providers_data = cur.fetchall()
            cur.close()
            conn.close()
    return render_template('admin.html', clients=clients_data, discounts=discounts_data, clients_orders=clients_orders_data, delivery_info=delivery_info_data, num_ordered_parts=num_ordered_parts_data, orders=orders_data, parts=parts_data, providers=providers_data)


@app.route('/update_clients', methods=['POST'])
def update_clients():
    conn = db_connection()
    cur = conn.cursor()

    # Обновление данных для каждого клиента
    for key in request.form:
        if key.startswith('full_name_'):
            client_id = key.split('_')[2]
            full_name = request.form[key]
            cur.execute("UPDATE clients SET full_name = %s WHERE client_id = %s", (full_name, client_id))
        elif key.startswith('phone_number_'):
            client_id = key.split('_')[2]
            phone_number = request.form[key]
            cur.execute("UPDATE clients SET phone_number = %s WHERE client_id = %s", (phone_number, client_id))
        elif key.startswith('email_'):
            client_id = key.split('_')[1]
            email = request.form[key]
            cur.execute("UPDATE clients SET email = %s WHERE client_id = %s", (email, client_id))
        elif key.startswith('delivery_address_'):
            client_id = key.split('_')[2]
            delivery_address = request.form[key]
            cur.execute("UPDATE clients SET delivery_address = %s WHERE client_id = %s", (delivery_address, client_id))
        elif key.startswith('client_status_'):
            client_id = key.split('_')[2]
            client_status = request.form[key]
            cur.execute("UPDATE clients SET client_status = %s WHERE client_id = %s", (client_status, client_id))
        elif key.startswith('status_level_'):
            client_id = key.split('_')[2]
            status_level = request.form[key]
            cur.execute("UPDATE clients SET status_level = %s WHERE client_id = %s", (status_level, client_id))

    # Обработка нового клиента
    new_full_name = request.form.get('new_full_name')
    new_phone_number = request.form.get('new_phone_number')
    new_email = request.form.get('new_email')
    new_delivery_address = request.form.get('new_delivery_address')
    new_client_status = request.form.get('new_client_status')
    new_status_level = request.form.get('new_status_level')

    if new_full_name and new_phone_number and new_email and new_delivery_address and new_client_status and new_status_level:
        cur.execute(
            "INSERT INTO clients (full_name, phone_number, email, delivery_address, client_status, status_level) VALUES (%s, %s, %s, %s, %s, %s)",
            (new_full_name, new_phone_number, new_email, new_delivery_address, new_client_status, new_status_level)
        )

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/admin')  # Перенаправление обратно на страницу admin


@app.route('/delete_client', methods=['POST'])
def delete_client():
    conn = db_connection()
    cur = conn.cursor()

    client_id = request.form['client_id']
    # Выполнение запроса на удаление клиента по его ID
    cur.execute("DELETE FROM clients WHERE client_id = %s", (client_id,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/admin')  # Перенаправление обратно на страницу admin


@app.route('/update_providers', methods=['POST'])
def update_providers():
    conn = db_connection()
    cur = conn.cursor()

    # Обновление данных для каждого поставщика
    for key in request.form:
        if key.startswith('provider_name_'):
            provider_id = key.split('_')[2]
            provider_name = request.form[key]
            cur.execute("UPDATE providers SET provider_name = %s WHERE provider_id = %s", (provider_name, provider_id))
        elif key.startswith('contact_person_'):
            provider_id = key.split('_')[2]
            contact_person = request.form[key]
            cur.execute("UPDATE providers SET contact_person = %s WHERE provider_id = %s", (contact_person, provider_id))
        elif key.startswith('phone_number_'):
            provider_id = key.split('_')[2]
            phone_number = request.form[key]
            cur.execute("UPDATE providers SET phone_number = %s WHERE provider_id = %s", (phone_number, provider_id))
        elif key.startswith('email_'):
            provider_id = key.split('_')[1]
            email = request.form[key]
            cur.execute("UPDATE providers SET email = %s WHERE provider_id = %s", (email, provider_id))
        elif key.startswith('address_'):
            provider_id = key.split('_')[1]
            address = request.form[key]
            cur.execute("UPDATE providers SET address = %s WHERE provider_id = %s", (address, provider_id))

    # Обработка нового клиента
    new_provider_name = request.form.get('new_provider_name')
    new_full_name = request.form.get('new_full_name')
    new_phone_number = request.form.get('new_phone_number')
    new_email = request.form.get('new_email')
    new_address = request.form.get('new_address')

    if new_provider_name and new_full_name and new_phone_number and new_email and new_address:
        cur.execute(
            "INSERT INTO providers (provider_name, contact_person, phone_number, email, address) VALUES (%s, %s, %s, %s, %s)",
            (new_provider_name, new_full_name, new_phone_number, new_email, new_address)
        )

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/admin')  # Перенаправление обратно на страницу admin


@app.route('/delete_provider', methods=['POST'])
def delete_provider():
    conn = db_connection()
    cur = conn.cursor()

    provider_id = request.form['provider_id']
    # Выполнение запроса на удаление клиента по его ID
    cur.execute("DELETE FROM providers WHERE provider_id = %s", (provider_id,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/admin')  # Перенаправление обратно на страницу admin


@app.route('/update_parts', methods=['POST'])
def update_parts():
    conn = db_connection()
    cur = conn.cursor()

    # Обновление данных для каждой детали
    for key in request.form:
        if key.startswith('part_name_'):
            part_id = key.split('_')[2]
            part_name = request.form[key]
            cur.execute("UPDATE parts SET part_name = %s WHERE part_id = %s", (part_name, part_id))
        elif key.startswith('country_prod_'):
            part_id = key.split('_')[2]
            country_prod = request.form[key]
            cur.execute("UPDATE parts SET country_prod = %s WHERE part_id = %s", (country_prod, part_id))
        elif key.startswith('producer_'):
            part_id = key.split('_')[1]
            producer = request.form[key]
            cur.execute("UPDATE parts SET producer = %s WHERE part_id = %s", (producer, part_id))
        elif key.startswith('price_'):
            part_id = key.split('_')[1]
            price = request.form[key]
            cur.execute("UPDATE parts SET price = %s WHERE part_id = %s", (price, part_id))
        elif key.startswith('brand_name_'):
            part_id = key.split('_')[2]
            brand_name = request.form[key]
            cur.execute("UPDATE parts SET brand_name = %s WHERE part_id = %s", (brand_name, part_id))
        elif key.startswith('model_name_'):
            part_id = key.split('_')[2]
            model_name = request.form[key]
            cur.execute("UPDATE parts SET model_name = %s WHERE part_id = %s", (model_name, part_id))
        elif key.startswith('year_'):
            part_id = key.split('_')[1]
            year = request.form[key]
            cur.execute("UPDATE parts SET year = %s WHERE part_id = %s", (year, part_id))

    # Обработка новой детали
    new_part_name = request.form.get('new_part_name')
    new_country_prod = request.form.get('new_country_prod')
    new_producer = request.form.get('new_producer')
    new_price = request.form.get('new_price')
    new_brand_name = request.form.get('new_brand_name')
    new_model_name = request.form.get('new_model_name')
    new_year = request.form.get('new_year')

    if new_part_name and new_country_prod and new_producer and new_price and new_brand_name and new_model_name and new_year:
        cur.execute(
            "INSERT INTO parts (part_name, country_prod, producer, price, brand_name, model_name, year) values (%s, %s, %s, %s, %s, %s, %s)",
            (new_part_name, new_country_prod, new_producer, new_price, new_brand_name, new_model_name, new_year)
        )

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/admin')  # Перенаправление обратно на страницу admin


@app.route('/delete_part', methods=['POST'])
def delete_part():
    conn = db_connection()
    cur = conn.cursor()

    part_id = request.form['part_id']
    # Выполнение запроса на удаление клиента по его ID
    cur.execute("DELETE FROM parts WHERE part_id = %s", (part_id,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/admin')  # Перенаправление обратно на страницу admin


@app.route('/update_orders', methods=['POST'])
def update_orders():
    conn = db_connection()
    cur = conn.cursor()

    # Обновление данных для каждой детали
    for key in request.form:
        if key.startswith('order_status_'):
            order_id = key.split('_')[2]
            order_status = request.form[key]
            cur.execute("UPDATE orders SET order_status = %s WHERE order_id = %s", (order_status, order_id))
        elif key.startswith('delivery_track_num_'):
            order_id = key.split('_')[3]
            delivery_track_num = request.form[key]
            cur.execute("UPDATE orders SET delivery_track_num = %s WHERE order_id = %s", (delivery_track_num, order_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/admin')  # Перенаправление обратно на страницу admin


@app.route('/delete_order', methods=['POST'])
def delete_order():
    conn = db_connection()
    cur = conn.cursor()

    order_id = request.form['order_id']
    # Выполнение запроса на удаление клиента по его ID
    cur.execute("DELETE FROM orders WHERE order_id = %s", (order_id,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/admin')  # Перенаправление обратно на страницу admin


if __name__ == "__main__":
    app.run(debug=True)