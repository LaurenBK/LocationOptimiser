from . models import CentralSite, Route, TransportClasses
from django.template import RequestContext
from django.http import HttpResponse
from django.shortcuts import render, render_to_response, redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib import auth
import django.contrib.auth.views as auth_views
from django import forms
from django.http import HttpResponseRedirect
from .forms import UserRegistrationForm

import pandas as pd
import numpy as np
import string
import googlemaps
import csv

import django_excel as excel
from bokeh.palettes import Set1
from django.contrib.auth.forms import UserCreationForm
from django.core.files.storage import FileSystemStorage
from bokeh.plotting import figure, output_file, show
from bokeh.models import Legend
from bokeh.embed import components

mykey = open("map_app/static/map_app/js/config.js", "r").readlines()[1]
mykey = mykey.split('\'')


class UploadFileForm(forms.Form):
    file = forms.FileField()


def delete_data(request):
    username = str(request.user)

    CentralSite.objects.filter(user=username).delete()
    Route.objects.filter(user=username).delete()
    TransportClasses.objects.filter(user=username).delete()
    return redirect('/map_app/home')


def login_view(request):
    username = request.POST.get('username', '')
    password = request.POST.get('password', '')
    user = auth.authenticate(username=username, password=password)
    if user is not None and user.is_active:
        # Correct password, and the user is marked "active"
        auth_views.login(request, user)
        # Redirect to a success page.
        return render(request, 'map_app/home.html')
    else:
        # Show an error page
        return render(request, 'registration/login.html')


def logout_view(request):
    auth_views.logout(request)
    # Redirect to a success page.
    return render(request, 'map_app/logout.html')


# def register(request):
#     if request.method == 'POST':
#         form = UserRegistrationForm(request.POST)
#         if form.is_valid():
#             userObj = form.cleaned_data
#             username = userObj['username']
#             email = userObj['email']
#             password = userObj['password']
#             if not (User.objects.filter(username=username).exists() or
#                 User.objects.filter(email=email).exists()):
#                 User.objects.create_user(username, email, password)
#                 user = auth.authenticate(username=username,
#                                          password=password)
#                 auth_views.login(request, user)
#                 return HttpResponseRedirect('/')
#             else:
#                 raise forms.ValidationError(
#                     'Looks like a username with that email'
#                     ' or password already exists')
#     else:
#         form = UserRegistrationForm()
#     return render(request, 'map_app/register.html', {'form': form})


def xlsx_reader(excel):
    """
    Helper function to get from xlsx to pandas df
    :param file: input file
    :return:
    """
    try:
        df = pd.read_excel(excel, 'Sheet1', encoding='utf8')
    except Exception as e:
        print(7, e)
        df = pd.read_excel(excel, encoding='utf8')
    return df


def country_checker(gmaps, latlng, country):
    reverse_geocode = gmaps.reverse_geocode(latlng)
    if reverse_geocode[0]['formatted_address'].split(',')[-1].strip() == country:
        return True
    else:
        return False


def process_address(address_string, country):
    translator = str.maketrans(string.punctuation,
                               ' ' * len(string.punctuation))
    address_string = address_string.translate(translator)
    address = address_string + ' South Africa'
    return address


def potential_site_processing(
        df: pd.DataFrame, user: str,  country: str='South Africa'):

    broken_addresses = []

    for i in range(len(df)):
        row = df.iloc[i, :]
        try:
            address = process_address(row['Address'], country)
            gmaps = googlemaps.Client(key=mykey[1])
            geocode_result = gmaps.geocode(address)
            try:
                latlng = geocode_result[0]['geometry']['location']
            except:
                latlng = geocode_result['geometry']['location']

            in_country_check = country_checker(gmaps, latlng, country)

            if not CentralSite.objects.filter(
                    address=row['Address'], user=user).exists() \
                    and in_country_check:
                query = CentralSite.objects.create(
                    user=user,
                    address=row['Address'],
                    pub_date=timezone.now(),
                    lat=latlng['lat'],
                    lng=latlng['lng'],
                    costPerMonth=0)
                query.save()
            addresses = [latlng['lat'], latlng['lng']]
        except Exception as e:
            print('Address broken. Error:', e, 'row', row)
            broken_addresses.append(row['Address'])

    return {'broken_addresses': broken_addresses}


def collections_site_processing(
        df: pd.DataFrame, user: str, country: str='South Africa'):

    broken_routes = []

    central = CentralSite.objects.order_by('pub_date')

    for i in range(len(df)):
        row = df.iloc[i, :]
        # print(row['Address'])
        try:
            address = row['Address'] + ' South Africa'
            gmaps = googlemaps.Client(key=mykey[1])
            geocode_result = gmaps.geocode(address)
            try:
                latlng = geocode_result[0]['geometry']['location']
            except Exception as e:
                print('geocode exception:', e)
                latlng = geocode_result['geometry']['location']

            in_country_check = country_checker(gmaps, latlng, country)

            # Calculate driving distance and add to database
            for c in central:
                distance_duration = gmaps.distance_matrix(
                    origins=c.address + ', South Africa',
                    destinations=row[0] + ', South Africa',
                    mode='driving')

                if not Route.objects.filter(
                        site=c, address=row['Address'], user=user).exists() \
                        and in_country_check:

                    query = Route.objects.create(
                        user=user,
                        site=c, address=row['Address'],
                        type=row['Collection vehicle'],
                        distance_km=round(
                            distance_duration['rows'][
                                0]['elements'][0][
                                'distance'][
                                'value'] / 1000.0, 2),
                        duration_minutes=round(
                            distance_duration['rows'][
                                0]['elements'][0][
                                'duration'][
                                'value'] / 60.0, 2),
                        deliveriesPerMonth=row[
                            'Collections per month'],
                        lat=latlng['lat'],
                        lng=latlng['lng'])
                    query.save()
        except Exception as e:
            print(e)
            broken_routes.append(row['Address'])

    return {'broken_routes': broken_routes}


def transport_types_processing(df: pd.DataFrame, user: str):
    for i in range(len(df)):
        row = df.iloc[i, :]
        try:
            query = TransportClasses.objects.create(
                user=user,
                transport=row['Collection vehicle'],
                costPerKm=row['Cost per km'])
            query.save()
        except Exception as e:
            print('2a', e)


# def broken_address_processing(addresses: list, user: str):
#     for i in range(len(addresses)):
#         try:
#             query = BrokenAddresses.objects.create(
#                 address=addresses[i],
#                 user=user)
#             query.save()
#         except Exception as e:
#             print('2b', e)
#

@ensure_csrf_cookie
def upload_page(request):

    # delete_data(request)

    upload_functions = {
        'potentialSitesFile': potential_site_processing,
        'collectionFile': collections_site_processing,
        'transportClassFile': transport_types_processing}
    file_present = None
    username = str(request.user)
    upload_occurred = False

    if request.method == 'POST'and request.FILES:
        df = {}
        for k in upload_functions.keys():
            try:
                excel = request.FILES[k]
                df[k] = xlsx_reader(excel)
                file_present = k
            except KeyError:
                pass
    else:
        df = None

    feedback = None
    if file_present is not None:
        feedback = upload_functions[file_present](
            df=df[file_present], user=username)
        upload_occurred = True

    context = {'upload_occurred': upload_occurred}
    try:
        central = CentralSite.objects.filter(
            user=username).order_by('pub_date')
        # context['central'] = True
        context['central_length'] = len(central)
    except Exception as e:
        print(4, e)
        pass

    try:
        routes = Route.objects.filter(
            user=username).order_by('site')

        # context['collections'] = True
        context['collections_length'] = len(
            list(set([r.address for r in routes])))
    except Exception as e:
        print(5, e)
        pass

    try:
        transport = TransportClasses.objects.filter(
            user=username).order_by('costPerKm')
        # context['transport'] = True
        context['transport_length'] = len(transport)
    except Exception as e:
        print(6, e)
        pass

    if feedback is not None:
        if 'broken_addresses' in feedback.keys():
            context['broken_addresses'] = feedback['broken_addresses']
            # broken_address_processing(feedback['broken_addresses'], username)
        if 'broken_routes' in feedback.keys():
            context['broken_routes'] = feedback['broken_routes']

    return render(request, 'map_app/home.html', context,
                  RequestContext(request))


@ensure_csrf_cookie
def otherLocations(request):

    username = str(request.user)
    central = CentralSite.objects.filter(
            user=username).order_by('pub_date')
    transport = TransportClasses.objects.filter(
            user=username).order_by('costPerKm')
    transport = {t.transport: t.costPerKm for t in transport}
    routes = Route.objects.filter(
            user=username).order_by('site')
    potential_addresses = [[c.lat, c.lng] for c in central]
    collection_addresses = [[r.lat, r.lng] for r in routes]
    for r in routes:
        r.routeCost = round(r.distance_km*transport[r.type], 2)
        r.routeCostPerMonth = round(r.distance_km *
                                    transport[r.type] *
                                    r.deliveriesPerMonth, 2)
        r.save()

    for c in central:
        y_temp = []
        for rt in routes:
            if rt.site == c:
                y_temp.append(rt.routeCostPerMonth)
        c.costPerMonth = sum(y_temp)
        c.save()

    sites = [(central[i].address,
             '{:,.2f}'.format(
                 central[i].costPerMonth, 2).replace(',', ' '))
             for i in range(len(central))]

    filtered = False
    selected_routes = []
    if request.method == 'POST':
        filtered = True
        site_to_filter = request.POST.get('filter_sites')
        selected_routes = Route.objects.filter(
            user=username, site=site_to_filter)

    num_routes = 0
    if len(central) > 0:
        num_routes = len(routes) / len(central)

    context = {'central': central,
               'num_routes': num_routes,
               'sites': sites,
               'potentialAddresses': potential_addresses,
               'collectionAddresses': collection_addresses}
    if filtered:
        context['selected_routes'] = selected_routes

    return render(request, 'map_app/otherLocations.html', context,
                  RequestContext(request))


def download_broken_addresses(request):
    username = str(request.user)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="broken_addresses.csv"'

    writer = csv.writer(response)
    broken_addresses = BrokenAddresses.objects.filter(user=username)

    writer.writerow(['Address'])
    print(broken_addresses)
    for address in broken_addresses:
        writer.writerow([address])

    return response


def downloadSummary(request):

    username = str(request.user)
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="summary.csv"'

    writer = csv.writer(response)
    central = CentralSite.objects.filter(
            user=username).order_by('pub_date')

    writer.writerow(['Address', 'Transport Cost Per Month'])
    for c in central:
        writer.writerow([str(c.address), str(c.costPerMonth)])

    return response


def downloadDetail(request):
    username = str(request.user)
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="detail.csv"'

    writer = csv.writer(response)
    routes = Route.objects.filter(
            user=username).order_by('site')

    writer.writerow(['Potential Site', 'Collection Site',
                     'Duration(min)', 'Distance(km)',
                     'Deliveries per month',
                     'Transport type', 'Route Cost(R)',
                     'Route Cost Per Month(R)'])

    for r in routes:
        writer.writerow([str(r.site), str(r.address),
                         str(r.duration_minutes),str(r.distance_km),
                         str(r.deliveriesPerMonth), str(r.type),
                         str(r.routeCost), str(r.routeCostPerMonth),])

    return response


def downloadOrderedByDistance(request):

    username = str(request.user)
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; ' \
                                      'filename="sitesByDistance.csv"'

    writer = csv.writer(response)
    routes = Route.objects.filter(
            user=username).order_by('distance_km')
    unique_routes = list(set([r.address for r in routes]))
    order = {}
    for add in unique_routes:
        temp_routes = routes.filter(address=add)
        order[add] = [r.site.address for r in temp_routes]

    header_row = ['Collection Point'] + ['Site %d'%x
        for x in range(len(order))]
    writer.writerow(header_row)

    for o in order.keys():
        content_row = [o] + order[o]
        writer.writerow(content_row)

    return response

# def summary(request):
#     central = CentralSite.objects.order_by('pub_date')
#     routes = Route.objects.order_by('site')
#     print([r.routeCost for r in routes])
#
#     title = 'Costs per km'
#
#     p = plot = figure(title= title ,
#         x_axis_label= 'Site Rent',
#         y_axis_label= 'Total Transport Cost per Month',
#         plot_width = 800,
#         plot_height =400,
#         toolbar_location="above")
#     x = [c.rent for c in central]
#     y = []
#     for c in central:
#         y_temp = []
#         for rt in routes:
#             if rt.site == c:
#                 y_temp.append(rt.routeCostPerMonth)
#         print('ytemp',y_temp)
#         y.append(sum(y_temp))
#     leg = []
#     for i in range(len(x)):
#         m = plot.circle(x[i], y[i], size=20, color = Set1[5][i])
#         leg.append((central[i].address,[m]))
#     legend = Legend(items = leg, location=(0, 100))
#     p.add_layout(legend,'right')
#
#     # Store components
#     script, div = components(plot)
#     print(central,x,y)
#     sites = {central[i].address:{'rent':central[i].rent,
#              'cost':y[i]} for i in range(len(central))}
#
#     context = {'script' : script , 'div' : div, 'sites':sites}
#     return render(request, 'map_app/summary.html', context )#,
#                   RequestContext(request))
#
