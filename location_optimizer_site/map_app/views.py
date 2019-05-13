from . models import PrimarySite, SecondarySite, TransportClasses
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
import xlrd
import numpy as np
import string
import googlemaps
import csv
import logging
import google
from collections import OrderedDict

import django_excel as excel
from bokeh.palettes import Set1
from django.contrib.auth.forms import UserCreationForm
from django.core.files.storage import FileSystemStorage
from bokeh.plotting import figure, output_file, show
from bokeh.models import Legend
from bokeh.embed import components


mykey = open("map_app/static/map_app/js/config.js", "r").readlines()[1]
mykey = mykey.split('\'')
gmaps = googlemaps.Client(key=mykey[1])


class UploadFileForm(forms.Form):
    file = forms.FileField()


def delete_data(request):
    username = str(request.user)

    PrimarySite.objects.filter(user=username).delete()
    SecondarySite.objects.filter(user=username).delete()
    TransportClasses.objects.filter(user=username).delete()
    return redirect('/map_app/home')


# def login_view(request):
#     username = request.POST.get('username', '')
#     password = request.POST.get('password', '')
#     user = auth.authenticate(username=username, password=password)
#     if user is not None and user.is_active:
#         # Correct password, and the user is marked "active"
#         auth_views.login(request, user)
#         # Redirect to a success page.
#         return render(request, 'map_app/home.html')
#     else:
#         # Show an error page
#         return render(request, 'registration/login.html')
#
#
# def logout_view(request):
#     auth_views.logout(request)
#     # Redirect to a success page.
#     return render(request, 'map_app/logout.html')


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
    df = None
    warning_message = None
    try:
        sheets = pd.read_excel(excel, sheet_name=None, encoding='utf8')
        for name, sheet in sheets.items():
            sheet.columns = [c.lower() for c in sheet.columns]
            if 'address' in sheet.columns:
                df = sheet
                if 'rent' not in df.columns:
                    df['rent'] = 0
            elif 'collection vehicle' in sheet.columns:
                df = sheet
        if df is None:  # this would mean that address was not present
            warning_message = 'No address was present in the upload'
            logging.error(warning_message)
        else:
            logging.info(
                f'Excel uploaded with format {name, sheet.columns in sheets.items()}')
    except xlrd.biffh.XLRDError:
        warning_message = 'Please upload utf8 encoded excel spreadsheet'
        logging.error(warning_message)
    return df, warning_message


def country_checker(gmaps, latlng, country):
    reverse_geocode = gmaps.reverse_geocode(latlng)
    if reverse_geocode[0]['formatted_address'].split(',')[-1].strip() == country:
        return True
    else:
        return False


def clean_address(address_string, country):
    address_string = address_string.lower()
    translator = str.maketrans(string.punctuation,
                               ' ' * len(string.punctuation))
    address_string = address_string.translate(translator)
    address = address_string + ' ' + country
    return address


def process_address(address, country):

    address = clean_address(address_string=address, country=country)
    geocode_result = gmaps.geocode(address)

    if len(geocode_result) > 0:
        geocode_result = geocode_result[0]

        latlng = geocode_result['geometry']['location']

        in_country_check = country_checker(gmaps, latlng, country)

        if in_country_check:
            return latlng
    else:
        return []


def primary_site_processing(
        df: pd.DataFrame, user: str,  country: str='South Africa'):

    feedback = {}
    broken_addresses = []

    n = 0
    for i in range(len(df)):
        row = df.iloc[i, :]

        latlng = process_address(address=row['address'], country=country)

        existence_check = PrimarySite.objects.filter(
            address=row['address'], user=user).exists()

        if len(latlng) == 0:
            broken_addresses.append(row['address'])
        elif not existence_check and latlng is not None:
            query = PrimarySite.objects.create(
                user=user,
                address=row['address'],
                pub_date=timezone.now(),
                lat=latlng['lat'],
                lng=latlng['lng'],
                costPerMonth=0)
            query.save()
            n += 1

    if len(broken_addresses) > 0:
        feedback['broken_primary'] = list(set(broken_addresses))

    if n > 0:
        feedback['num_primary'] = n

    return feedback


def secondary_site_processing(
        df: pd.DataFrame, user: str, country: str='South Africa'):

    feedback = {}
    broken_secondary_sites = []

    primary = PrimarySite.objects.filter(user=user).order_by('pub_date')

    n = 0
    for i in range(len(df)):
        row = df.iloc[i, :]

        latlng = process_address(address=row['address'], country=country)

        # Calculate driving distance and add to database

        for c in primary:
            distance_duration = gmaps.distance_matrix(
                origins=c.address + ', South Africa',
                destinations=row['address'] + ', South Africa',
                mode='driving')

            existence_check = SecondarySite.objects.filter(
                site=c, address=row['address'], user=user).exists()

            if len(latlng) == 0:
                broken_secondary_sites.append(row['address'])
            elif not existence_check and latlng is not None:

                distance_km = round(
                    distance_duration['rows'][0]['elements'][0][
                        'distance']['value'] / 1000.0, 2)

                duration = round(
                    distance_duration['rows'][0]['elements'][0][
                        'duration']['value'] / 60.0, 2)

                query = SecondarySite.objects.create(
                    user=user,
                    site=c, address=row['address'],
                    type=row['collection vehicle'],
                    distance_km=distance_km,
                    duration_minutes=duration,
                    deliveriesPerMonth=row[
                        'collections per month'],
                    lat=latlng['lat'],
                    lng=latlng['lng'])
                query.save()
                n += 1

    if len(broken_secondary_sites) > 0:
        feedback['broken_secondary'] = broken_secondary_sites

    if n > 0:
        feedback['num_secondary_sites'] = n

    return feedback


def transport_types_processing(df: pd.DataFrame, user: str):

    feedback = {}

    n = 0
    for i in range(len(df)):
        row = df.iloc[i, :]
        try:
            query = TransportClasses.objects.create(
                user=user,
                transport=row['collection vehicle'],
                costPerKm=row['cost per km'])
            query.save()
            n += 1
        except Exception as e:
            print(e)

    if n > 0:
        feedback['num_transport'] = n

    return feedback


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

    context = {}

    upload_functions = OrderedDict(
        primarySitesFile=primary_site_processing,
        secondaryFile=secondary_site_processing,
        transportClassFile=transport_types_processing)
    file_present = []
    username = str(request.user)
    warning_message = None

    if request.method == 'POST' and request.FILES:
        dfs = {}
        for k in upload_functions.keys():
            try:
                excel = request.FILES[k]
                dfs[k], warning_message = xlsx_reader(excel)
                file_present.append(k)
            except KeyError:
                pass
    else:
        dfs = None

    feedback = {}
    for k in range(len(file_present)):
        file_type = file_present[k]
        feedback[file_type] = upload_functions[file_type](
            df=dfs[file_type], user=username)

    try:
        context['primary_length'] = PrimarySite.objects.filter(
            user=username).count()
    except Exception as e:
        print(e)
        logging.debug(f'No primary sites uploaded: {e}')

    try:
        context['secondary_length'] = SecondarySite.objects.filter(
            user=username).count()
    except Exception as e:
        print(e)
        logging.debug(f'No secondary sites uploaded {e}')

    try:
        context['transport_length'] = TransportClasses.objects.filter(
            user=username).count()
    except Exception as e:
        logging.debug(f'No transport types uploaded {e}')
        pass

    for key, data in feedback.items():
        # this will add broken sites, secondary sites and transport
        context.update(data)

    if warning_message is not None:
        context['warning_message'] = warning_message

    print(context)

    if context['primary_length'] == 0 or \
        context['secondary_length'] == 0 or \
        context['transport_length'] == 0:
            context['disable'] = True

    return render(request, 'map_app/home.html', context,
                  RequestContext(request))


@ensure_csrf_cookie
def comparePrimary(request):

    username = str(request.user)
    primary = PrimarySite.objects.filter(
            user=username).order_by('pub_date')
    transport = TransportClasses.objects.filter(
            user=username).order_by('costPerKm')
    transport = {t.transport: t.costPerKm for t in transport}
    secondary = SecondarySite.objects.filter(
            user=username).order_by('site')
    primary_addresses = [[p.lat, p.lng] for p in primary]
    secondary_addresses = [[s.lat, s.lng] for s in secondary]

    for r in secondary:
        if r.SiteCost == 0:
            r.SiteCost = round(r.distance_km*transport[r.type], 2)
            r.SiteCostPerMonth = round(r.distance_km *
                                        transport[r.type] *
                                        r.deliveriesPerMonth, 2)
            r.save()

    for p in primary:
        y_temp = []
        for rt in secondary:
            if rt.site == p:
                y_temp.append(rt.SiteCostPerMonth)
        p.costPerMonth = sum(y_temp)
        p.save()

    sites = [(primary[i].address,
             '{:,.2f}'.format(
                 primary[i].costPerMonth, 2).replace(',', ' '))
             for i in range(len(primary))]

    filtered = False
    selected_secondary = []
    if request.method == 'POST':
        filtered = True
        site_to_filter = request.POST.get('filter_sites')
        site_id = primary.filter(address=site_to_filter).values()[0]['id']
        selected_secondary = SecondarySite.objects.filter(
            user=username, site=site_id)

    num_secondary = 0
    if len(primary) > 0:
        num_secondary = len(secondary) / len(primary)
    print(num_secondary)

    context = {'primary': primary,
               'num_secondary': num_secondary,
               'sites': sites,
               'primaryAddresses': primary_addresses,
               'secondaryAddresses': secondary_addresses}
    if filtered:
        context['selected_secondary'] = selected_secondary

    return render(request, 'map_app/comparePrimary.html', context,
                  RequestContext(request))


@ensure_csrf_cookie
def closestSiteCosts(request):

    username = str(request.user)
    primary = PrimarySite.objects.filter(
            user=username).order_by('pub_date')
    transport = TransportClasses.objects.filter(
            user=username).order_by('costPerKm')
    transport = {t.transport: t.costPerKm for t in transport}
    secondary = SecondarySite.objects.filter(
            user=username).order_by('site')
    primary_addresses = [[p.lat, p.lng] for p in primary]
    secondary_addresses = [[s.lat, s.lng] for s in secondary]

    for r in secondary:
        if r.SiteCost == 0:
            r.SiteCost = round(r.distance_km*transport[r.type], 2)
            r.SiteCostPerMonth = round(r.distance_km *
                                        transport[r.type] *
                                        r.deliveriesPerMonth, 2)
            r.save()

    primary_df = pd.DataFrame.from_records(primary.values()).rename(
        columns={'id': 'site_id', 'address': 'p_address'})
    sites_to_toggle = primary_df.p_address

    secondary_df = pd.DataFrame.from_records(secondary.values())

    df = pd.merge(primary_df[['site_id', 'p_address']], secondary_df,
                  on='site_id', how='inner')

    toggled = False
    if request.method == 'POST':
        toggled = True
        sites_to_toggle = request.POST.getlist('toggle_sites')

    df_filtered = df[df['p_address'].isin(sites_to_toggle)]

    print(df.shape, sites_to_toggle,
          df_filtered)

    df_filtered = df_filtered.loc[df_filtered.groupby(
        "address")["SiteCostPerMonth"].idxmin()]
    site_costs = df_filtered.groupby('p_address')[
        "SiteCostPerMonth"].sum().reset_index()
    site_costs['SiteCostPerMonth'] = site_costs['SiteCostPerMonth'].apply(
        lambda x: '{:,.2f}'.format(x).replace(',', ' '))

    sites = site_costs.values.tolist()

    num_secondary = 0
    if len(primary) > 0:
        num_secondary = len(secondary) / len(primary)

    context = {
        'primary': primary,
               # 'num_secondary': num_secondary,
               'sites': sites,
               'primaryAddresses': primary_addresses,
               'secondaryAddresses': secondary_addresses}

    return render(request, 'map_app/closestSiteCosts.html', context,
                  RequestContext(request))


# def download_broken_addresses(request):
#     username = str(request.user)
#
#     response = HttpResponse(content_type='text/csv')
#     response['Content-Disposition'] = 'attachment; filename="broken_addresses.csv"'
#
#     writer = csv.writer(response)
#     broken_addresses = BrokenAddresses.objects.filter(user=username)
#
#     writer.writerow(['Address'])
#     print(broken_addresses)
#     for address in broken_addresses:
#         writer.writerow([address])
#
#     return response


def downloadSummary(request):

    username = str(request.user)
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="summary.csv"'

    writer = csv.writer(response)
    central = PrimarySite.objects.filter(
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
    secondary = SecondarySite.objects.filter(
            user=username).order_by('site')

    writer.writerow(['Potential Site', 'Collection Site',
                     'Duration(min)', 'Distance(km)',
                     'Deliveries per month',
                     'Transport type', 'Site Cost(R)',
                     'Site Cost Per Month(R)'])

    for s in secondary:
        writer.writerow([str(s.site), str(s.address),
                         str(s.duration_minutes), str(s.distance_km),
                         str(s.deliveriesPerMonth), str(s.type),
                         str(s.SiteCost), str(s.SiteCostPerMonth)])

    return response


def downloadOrderedByDistance(request):

    username = str(request.user)
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; ' \
                                      'filename="sitesByDistance.csv"'

    writer = csv.writer(response)

    num_primary = PrimarySite.objects.filter(
            user=username).count()

    secondary = SecondarySite.objects.filter(
            user=username).order_by('distance_km')

    order = {}
    header_row = ['Secondary Site'] + [
        'Site %d' % x for x in range(1, num_primary + 1)]

    unique_secondary = list(set([r.address for r in secondary]))
    for add in unique_secondary:
        temp_secondary = SecondarySite.objects.filter(address=add)
        order[add] = [r.site.address for r in temp_secondary]

    writer.writerow(header_row)

    for o in order.keys():
        content_row = [o] + order[o]
        writer.writerow(content_row)

    return response

# def summary(request):
#     central = PrimarySite.objects.order_by('pub_date')
#     SecondarySites = SecondarySite.objects.order_by('site')
#     print([r.SecondarySiteCost for r in SecondarySites])
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
#         for rt in SecondarySites:
#             if rt.site == c:
#                 y_temp.append(rt.SecondarySiteCostPerMonth)
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
