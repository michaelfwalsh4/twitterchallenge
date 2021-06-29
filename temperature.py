from fpdf import FPDF
import os
import shutil
import gdown
import pandas as pd
import matplotlib
import numpy as np

if os.path.isfile('Temperature Data.csv'):
    print("Temperature Data exists")
else:
    print("Temperature Data does not exist. Downloading from Google Drive...")
    url = 'https://drive.google.com/uc?id=1-C14CqarebgCFYN9ZsP2AtgY98tbuGGS'
    output = 'Temperature Data.csv'
    gdown.download(url, output, quiet=True)

if os.path.isfile('Population Data.csv'):
    print("Population Data exists")
else:
    print("Population Data does not exist. Downloading from Google Drive...")
    url = 'https://drive.google.com/uc?id=1DquEztoGTKLVOyLd9wdNoEgMW38zi_qU'
    output = 'Population Data.csv'
    gdown.download(url, output, quiet=True)

print("Determining Pop. Weighted Temp...")

pop = pd.read_csv('Population Data.csv')
data = pd.read_csv('Temperature Data.csv')
states = pd.pivot_table(pop, index='State', values='population',aggfunc='sum').reset_index()

data['date']=pd.to_datetime(data['location_date'],errors='ignore')

piv = pd.pivot_table(data,index='date',columns='name',values='temp_mean_c')

clean_temp_pivot = piv.fillna(method='ffill').reset_index()

agg_temp = pd.melt(clean_temp_pivot, id_vars='date')
big_table = agg_temp.merge(pop, left_on = 'name', right_on='City')
big_table['bigtemp']=big_table['population']*big_table['value']
big_table=big_table.merge(states, on='State')

big_table_pivot = pd.pivot_table(big_table, index = 'date', columns ='State', values='value',aggfunc='mean')
for col in big_table_pivot.columns:
    big_table_pivot[col]=big_table_pivot[col]*states[states['State']==col].population.values[0]

population = 0
for col in big_table_pivot.columns:
    population = population + states[states['State']==col].population.values[0]

big_table_pivot['pop_weighted_temp']=big_table_pivot.sum(axis=1)/population

wtd_temp = big_table_pivot['pop_weighted_temp'].reset_index()
wtd_temp.to_csv('poptemp.csv',index=False)

wtd_temp['month-day']= wtd_temp['date'].dt.strftime('%m-%d')
wtd_temp['month']= wtd_temp['date'].dt.strftime('%m')
wtd_temp['case']= wtd_temp['date'].dt.strftime('%Y')
wtd_temp_piv = pd.pivot_table(wtd_temp, index='month-day', columns='case',values='pop_weighted_temp')
wtd_temp_piv['mean']=wtd_temp_piv.mean(axis=1)
wtd_temp_piv['max']=wtd_temp_piv.max(axis=1)
wtd_temp_piv['min']=wtd_temp_piv.min(axis=1)

print("Plotting...")
# create temp dir
if not os.path.exists('img'):
    os.makedirs('img')

ax = wtd_temp_piv.plot(y=['mean','min','max'])
fig =ax.get_figure()
ax.set_title('Seasonal Population Weighted Temperature')
legend = ax.legend()
legend.title=''
fig.savefig('img/pop_wtd_temp.png')

monthly_max = pd.pivot_table(wtd_temp, index = 'month', values = 'pop_weighted_temp',aggfunc=max)
monthly_mean = pd.pivot_table(wtd_temp, index = 'month', values = 'pop_weighted_temp',aggfunc='mean')
monthly_min = pd.pivot_table(wtd_temp, index = 'month', values = 'pop_weighted_temp',aggfunc=min)
monthly = pd.concat([monthly_mean,monthly_max,monthly_min],axis=1)
monthly.columns = ['mean','max','min']

ax = monthly.plot(y=['mean','min','max'])
fig =ax.get_figure()
ax.set_title('Monthly Pop Weighted Temps')
legend = ax.legend()
legend.title=''
fig.savefig('img/monthly_pop_wtd_temp.png')

def plot_missing(input_data,name):
    filled = pd.DataFrame(input_data.fillna(100))
    filled['was filled']=filled.max(axis=1)#axis=1
    forecasted= filled[filled['was filled']==100]['was filled']
    #print(forecasted)
    
    actual_and_forecasted = pd.DataFrame(input_data).merge(forecasted, on='date',how='left').reset_index()
    actual_and_forecasted['missing']= np.where(actual_and_forecasted['was filled']==100, clean_temp_pivot[col],np.nan)

    ax.cla()
    ax2=actual_and_forecasted.plot(x=['date'], y=['missing'],label='Missing/Projected Value',kind='scatter',color='red',zorder=2)
    actual_and_forecasted.plot(x='date',y=name,label='Pop Wtd. Temp',kind='line',ax=ax2,zorder=1)

    ax2.legend()
    fig =ax2.get_figure()
    ax2.set_title(f'Actual and Projected Data: {name}')
    ax2.set_ylabel('Pop Weighted Temp')
    import matplotlib.dates as mdates
    myFmt = mdates.DateFormatter('%b %y')
    ax2.xaxis.set_major_formatter(myFmt)

    name = name.replace('/','')
    fig.savefig(f'img/{name}.png')
    ax2.cla()
    matplotlib.pyplot.close()
    return f'img/{name}.png'

imagelist = ['img/pop_wtd_temp.png','img/monthly_pop_wtd_temp.png']

'''
#print(piv)
#item = plot_missing(piv,'data')
#imagelist.append(item)
'''

for col in piv.columns[:-1]:
    item = plot_missing(piv[col],col)
    imagelist.append(item)

pdf = FPDF()

check = True
pdf.add_page()
for image in imagelist:
    if(check):
        pdf.image(image,w=140)
        check  = False
    else:
        pdf.image(image,y=140,w=140)
        pdf.add_page()
        check = True

pdf.output("viz.pdf", "F")

shutil.rmtree('img')
os.remove('Population Data.csv')
os.remove('Temperature Data.csv')
print("Results are stroed in 'poptemp.csv' and 'viz.pdf'")