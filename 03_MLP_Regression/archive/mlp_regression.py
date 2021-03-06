import torch
import torch.nn as nn

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

#=====================================================================================
# Data Loading
#=====================================================================================

# Read in the medical insurance data
df = pd.read_csv('https://raw.githubusercontent.com/StatsGary/Data/main/insurance.csv')

#=====================================================================================
# Feature Engineering
#=====================================================================================
# Encode the categorical features
cat_cols = ['sex', 'smoker', 'region', 'children']
cont_cols = ['age', 'bmi']

# Set the target (y) column
y = ['charges']

# CONVERT CATEGORICAL COLUMNS
for cat in cat_cols:
    df[cat] = df[cat].astype('category')

# Get the cat codes for each of the categorical values
cats = np.stack([df[col].cat.codes.values for col in cat_cols],axis=1)

# Convert this to a tensor
cats = torch.tensor(cats, dtype=torch.int64)
print(cats[:5])

cat_sizes = [len(df[col].cat.categories) for col in cat_cols]
print(cat_sizes)
# Get embedding sizes
emb_szs = [(size, min(50,(size+1)//2)) for size in cat_sizes]
print(emb_szs)

# CONVERT CONTINUOUS VARIABLES
cont_cols = np.stack([df[col].values for col in cont_cols], axis=1)
cont_cols = torch.tensor(cont_cols, dtype=torch.float)#.reshape(-1,1)
print(cont_cols)

#CONVERT TARGET (Y) LABEL
y = torch.tensor(df[y].values,dtype=torch.float).reshape(-1,1)
print(cats.shape, cont_cols.shape, y.shape)

#=====================================================================================
# 
#=====================================================================================
selfembeds = nn.ModuleList([nn.Embedding(ne,nf) for ne, nf in emb_szs])
print(selfembeds)
cat_szs = [len(df[col].cat.categories) for col in cat_cols]
emb_szs = [(size, min(50, (size+1)//2)) for size in cat_szs]
emb_szs

# Create the torch model
class MLPRegressor(nn.Module):
    def __init__(self, emb_szs, n_cont, out_sz, layers, p=0.5):
        super().__init__()
        self.embeds = nn.ModuleList([nn.Embedding(ni, nf) for ni,nf in emb_szs])
        self.emb_drop = nn.Dropout(p)
        self.bn_cont = nn.BatchNorm1d(n_cont)
        
        layerlist = []
        n_emb = sum((nf for ni,nf in emb_szs))
        n_in = n_emb + n_cont
        
        for i in layers:
            layerlist.append(nn.Linear(n_in,i)) 
            layerlist.append(nn.ReLU(inplace=True))
            layerlist.append(nn.BatchNorm1d(i))
            layerlist.append(nn.Dropout(p))
            n_in = i
        layerlist.append(nn.Linear(layers[-1],out_sz))
            
        self.layers = nn.Sequential(*layerlist)
    
    def forward(self, x_cat, x_cont):
        embeddings = []
        for i,e in enumerate(self.embeds):
            embeddings.append(e(x_cat[:,i]))
        x = torch.cat(embeddings, 1)
        x = self.emb_drop(x)
        
        x_cont = self.bn_cont(x_cont)
        x = torch.cat([x, x_cont], 1)
        x = self.layers(x)
        return x

# Define model 
torch.manual_seed(123)
model = MLPRegressor(emb_szs, 
                    cont_cols.shape[1],
                    1,
                    [200,100], p=0.4)



print(model)

# Split data
batch_size = 60000
test_size = int(batch_size * 2)

cat_train = cats[:batch_size-test_size]
cat_test = cats[batch_size-test_size:batch_size]
con_train = cont_cols[:batch_size-test_size]
con_test = cont_cols[batch_size-test_size:batch_size]
y_train = y[:batch_size-test_size:batch_size]
y_test = y[batch_size-test_size:batch_size]



#Create the loss function and optimizer
import time
def train(category_train, continous_train,y_training, learn_rate=0.001, epochs=300):
    print('[INFO] starting training')
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learn_rate)
    start_time = time.time()
    epochs = epochs
    # Create empty list to capture the losses
    losses = []
    for i in range(epochs):
        i+=1
        y_pred = model(cat_train, con_train)
        loss = torch.sqrt(criterion(y_pred, y_train)) #RMSE
        # Append losses to empty list
        losses.append(loss)
        if i%25 == 1:
            print(f'epoch: {i:3}  loss: {loss.item():10.8f}')

        # Clear the gradient tape
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    print(f'epoch: {i:3}  loss: {loss.item():10.8f}') # print the last line
    print(f'\nDuration: {time.time() - start_time:.0f} seconds') # print the time elapsed


# Train the model
train(cat_train, con_train, y_train, epochs=400)


