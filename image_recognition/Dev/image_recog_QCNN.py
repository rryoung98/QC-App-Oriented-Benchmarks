
# Importing the required libraries for the project

import pandas as pd
import numpy as np
from sklearn.datasets import fetch_openml
from sklearn.model_selection import train_test_split
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from qiskit import QuantumCircuit, Aer, transpile,execute
from qiskit.circuit.library import RealAmplitudes
from sklearn.metrics import accuracy_score,log_loss
from qiskit.circuit import ParameterVector
from qiskit.opflow.primitive_ops import PauliSumOp
from qiskit.quantum_info import SparsePauliOp

import expectation_calc_qcnn

global expectation_calc_method

# change the below variable to True if you want to use expectation_calc.py file for expectation value calculation
expectation_calc_method = True

# Dev Note :- Each image has Intensity from 0 to 255

''' All steps are explained below
    1. Fetch the MNIST dataset
    2. Access the data and target  
        i) filter the data with 7 and 9 ( for initial development we are doing binary classification )
    3. Split the data into train and test data ( 80% for training and 20% for testing )
    4. pca for dimensionality reduction (x_scaled_data is the scaled data)
    5. batching the data ( we are not using batching for now)
    6. custom varational circuit is defined for now instead of QCNN (var_circuit)
        i)   it will be updated once we have the QCNN
    7. Input data is encoded into quantum state and then passed through the custom variational circuit(qcnn_model)
   
   8):- loss function is not minimized proply to get convergance and possible reasons are 
        i) we are not encoding the data properly into quantum state 
        ii) expectation value calcuation needs to be improved
        ii) cobyla optimizer coulen't find the minimum value
        iv) we need to check if we need to use classical neural network to extract labels from the circuit output
        
    8. loss function is defined (loss) as our objective is to minimize the loss ( Currently changes are in progess)
        i)   Function to predict the label ( 0,1) from circuit output is 
        ii)  loss function is pending and will be updated once the above function is done
        iii) need to check if to use classical neural network to extract labels from the circuit output
    9. Optimizer is defined (optimizer) 
    
    10. Testing the model (Pending :-  Improve the code to test the model on test data)
    '''
    # Pending
    #   To Find common expectatation value code & other additional functionality for 8 qubits
    

global num_qubits

# Number of qubits for the quantum circuit
num_qubits = 8

# Fetch the MNIST dataset from openml
mnist = fetch_openml('mnist_784')

# Access the data and target
# x has all the pixel values of image and has Data shape of (70000, 784)  here 784 is 28*28
x = mnist.data
print("shape of x:",x.shape)

# y has all the labels of the images and has Target shape of (70000,)
y = mnist.target
print("shape of y:",y.shape)


# convert the given y data to integers so that we can filter the data
y = y.astype(int)

# Filtering only values with 7 or 9 as we are doing binary classification for now and we will extend it to multi-class classification
binary_filter = (y == 0) | (y == 1)

# Filtering the x and y data with the binary filter
x = x[binary_filter]
y = y[binary_filter]

# create a new y data with 0 and 1 values with 7 as 0 and 9 as 1 so that we can use it for binary classification
# y = (y == 9).astype(int)


''' Here X_train has all the training pixel values of image (i.e, 80% ) and has Data shape of (56000, 784) here 784 is 28*28
    Here y_train has all the training labels of the images (i.e, 80% ) and has Target shape of (56000,)
    
    Here X_test has all the testing pixel values of images (i.e, 20% ) and has Data shape of (14000, 784) 
    Here y_test has all the testing labels of the images (i.e, 20% ) and has Target shape of (14000,)'''

# Here we have only two classes data out of above mentioned data    
x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)
# print(x.shape, y.shape, x_train.shape, y_train.shape, x_test.shape, y_test.sha?pe)

# Reduce the size of the dataset to 200 training samples and 50 test samples for faster execution 
# will be removed once the code is ready for final execution
x_train = x_train[:200]
y_train = y_train[:200]
x_test  = x_test[:50]
y_test  = y_test[:50]

# After initial development  below code will be move to qubit loop
# -------------- PCA Compression -----------------
# Number of principal components to keep as of now it is 14 
pca = PCA(n_components = num_qubits)
# pca = PCA( ) if pca_check == True else PCA(n_components = num_qubits)


# Apply PCA on the data to reduce the dimensions and it is in the form of 'numpy.ndarray'
x_train_pca = pca.fit_transform(x_train)
x_test_pca =  pca.fit_transform(x_test)


# Create an instance of MinMaxScaler
scaler = MinMaxScaler(feature_range=(0, 2 * np.pi))


# Apply min-max scaling to the data to bring the values between 0 and 1
x_scaled_test =  scaler.fit_transform(x_test_pca)
x_scaled_train = scaler.fit_transform(x_train_pca)




# Define the convolutional circuits
def conv_circ_1(params, first, second):
    # Your implementation for conv_circ_1 function here
    conv_circ = QuantumCircuit(8)
    conv_circ.rx(params[0], first)
    conv_circ.rx(params[1], second)
    conv_circ.rz(params[2], first)
    conv_circ.rz(params[3], second)
    conv_circ.crx(params[4], second, first)  
    conv_circ.crx(params[5], first, second)
    conv_circ.rx(params[6], first)
    conv_circ.rx(params[7], second)
    conv_circ.rz(params[8], first)
    conv_circ.rz(params[9], second)
    return conv_circ

# Define the pooling circuits
def pool_circ_1(params, first, second):
    # Your implementation for pool_circ_1 function here
    pool_circ = QuantumCircuit(8)
    pool_circ.crz(params[0], first, second)
    pool_circ.x(second)
    pool_circ.crx(params[1], first, second)
    return pool_circ

def pool_circ_2(first, second):
    pool_circ = QuantumCircuit(8)
    pool_circ.crz(first, second)
    return pool_circ

# Quantum Circuits for Convolutional layers
def conv_layer_1(qc, params):
    qc = qc.compose(conv_circ_1(params, 0, 1))
    qc = qc.compose(conv_circ_1(params, 2, 3))
    qc = qc.compose(conv_circ_1(params, 4, 5))
    qc = qc.compose(conv_circ_1(params, 6, 7))
    return qc

def conv_layer_2(qc, params):
    qc = qc.compose(conv_circ_1(params, 0, 2))
    qc = qc.compose(conv_circ_1(params, 4, 6))
    return qc

def conv_layer_3(qc, params):
    qc = qc.compose(conv_circ_1(params, 0, 4))
    return qc

# Quantum Circuits for Pooling layers
def pooling_layer_1(qc, params):
    qc = qc.compose(pool_circ_1(params, 1, 0))
    qc = qc.compose(pool_circ_1(params, 3, 2))
    qc = qc.compose(pool_circ_1(params, 5, 4))
    qc = qc.compose(pool_circ_1(params, 7, 6))
    return qc

def pooling_layer_2(qc, params):
    qc = qc.compose(pool_circ_1(params, 0, 2))
    qc = qc.compose(pool_circ_1(params, 4, 6))
    return qc

def pooling_layer_3(qc, params):
    qc = qc.compose(pool_circ_1(params, 0, 4))
    return qc

# Variational circuit used in below model which has parameters optimized during training
def qcnn_circ(num_qubits, params, U_params=10):
    qc = QuantumCircuit(num_qubits,1)  # just to measure the 5 th qubit (4 indexed)
    param1 = params[0:U_params]
    param2 = params[U_params: 2 * U_params]
    param3 = params[2 * U_params: 3 * U_params]
    param4 = params[3 * U_params: 3 * U_params + 2]
    param5 = params[3 * U_params + 2: 3 * U_params + 4]
    param6 = params[3 * U_params + 4: 3 * U_params + 6]

    # Pooling Ansatz1 is used by default
    qc = conv_layer_1(qc, param1)
    qc = pooling_layer_1(qc, param4)
    qc = conv_layer_2(qc, param2)
    qc = pooling_layer_2(qc, param5)
    qc = conv_layer_3(qc, param3)
    qc = pooling_layer_3(qc, param6)

    return qc


# model to be used for training which has input data encoded and variational circuit is appended to it
def qcnn_model(theta, x, num_qubits, reps):
    
    qc = QuantumCircuit(num_qubits)
      
    # Encode the pixel data into the quantum circuit here  x is the input data which is list of 14 values   
    # feature mapping 
    for j in range(num_qubits):
        qc.rx(x[j], j )
    # Append the variational circuit ( Ansatz ) to the quantum circuit
    params = theta.tolist()
    qcnn_circ_temp = qcnn_circ(num_qubits, params)
    qc.compose(qcnn_circ_temp, inplace=True)
    return qc


# Define the quantum instance to be used for training
backend = Aer.get_backend('qasm_simulator')

# threshold to be used for prediction of label from the circuit output
global threshold 

threshold = 0.5
    

# for training loss plot 

train_loss_history = []
train_accuracy_history = []
global num_iter_plot 


# function to calculate the loss function
def loss_function(theta, is_draw_circ=True, is_print=True):

    prediction_label = []
    i_draw = 0
    for data_point, label in zip(x_scaled_train, y_train):
        # Create the quantum circuit for the data point
        qc = qcnn_model(theta, data_point, num_qubits, reps)

        if i_draw==0 and is_draw_circ:
            print(qc)
            i_draw += 1

        # Simulate the quantum circuit and get the result
        if expectation_calc_method == True:
            val = expectation_calc_qcnn.calculate_expectation(qc,shots=num_shots,num_qubits=num_qubits)  
            print(val)  
            val=(val+1)*0.5
        prediction_label.append(val)
        
    loss = log_loss(y_train, prediction_label)

    if is_print:
        predictions = []
        for i in range(len(y_train)):
            if prediction_label[i] > 0.5:
                predictions.append(1)
            else:
                predictions.append(0)
        # print(predictions)
        accuracy = accuracy_score(y_train, predictions)
        print("Accuracy:", accuracy, "loss:", loss)
        train_loss_history.append(loss)
        train_accuracy_history.append(accuracy)
    
    return loss

# print(len(train_loss_history))

def callback(theta):
    pass
        # loss_function(theta, is_draw_circ=False, is_print=True)

# Initialize  epochs
num_epochs = 1
reps = 3

# Number of shots to run the program (experiment)
num_shots = 1000

# Initialize the weights for the QNN model
np.random.seed(0)
# weights = np.random.rand(num_qubits * reps *2 )
weights = np.random.rand(36)
#weights = np.zeros(num_qubits * reps)
print(len(weights))

# Will increase the number of epochs once the code is fine tuned to get convergance 
for epoch in range(num_epochs):
    # Minimize the loss using SPSA optimizer
    theta = minimize(loss_function, x0 = weights, method="COBYLA", tol=0.001, callback=callback, options={'maxiter': 100, 'disp': False} )
    #theta=SPSA(maxiter=100).minimize(loss_function, x0=weights)

    loss = theta.fun
    print(f"Epoch {epoch+1}/{num_epochs}, loss = {loss:.4f}")

print("theta function", theta)
    # print(type(theta.x))

# Below code is to test the model on test data after training and getting theta values
# Perform inference with the trained QNN
predictions = []

# Loop over the test data and use theta obtained from training to get the predicted label
#print("x_scaled_test",x_scaled_test)
# print(theta.x)
# print(num_shots)
test_accuracy_history = []
for data_point in x_scaled_test:
    qc = qcnn_model(theta.x, data_point, num_qubits, reps)
        # Simulate the quantum circuit and get the result
    if expectation_calc_method == True:
        val = expectation_calc_qcnn.calculate_expectation(qc,shots=num_shots,num_qubits=num_qubits)   
        val=(val+1)*0.5
        if val > 0.5:
            predicted_label = 1
        else:
            predicted_label = 0
    print("predicted_label",predicted_label)
    predictions.append(predicted_label)
    
    # Calculate the test accuracy on the test set after each data point
    test_accuracy = accuracy_score(y_test[:len(predictions)], predictions)

    # Store the test accuracy in the history list after each data point
    test_accuracy_history.append(test_accuracy)


# Evaluate the QCNN accuracy on the test set once the model is trained and tested
accuracy = accuracy_score(y_test, predictions)
print("Accuracy:", accuracy)
print(f"This is for {num_qubits} qubits")
print("predictions",predictions)


# training loss after each iteration
# plt.plot(range(1, num_epochs * 100 + 1), train_loss_history)
plt.plot(range(1, len(train_loss_history)+1), train_loss_history)
plt.xlabel('Iteration')
plt.ylabel('Training Loss')
plt.title(f'Training Loss History for {num_qubits} qubits')
plt.show()

# training accuracy after each iteration
plt.plot(range(1, len(train_accuracy_history)+1), train_accuracy_history)
plt.xlabel('Iteration')
plt.ylabel('Training Accuracy')
plt.title(f'Training Accuracy History for {num_qubits} qubits')
plt.show()


# testing accuracy after each data point
plt.plot(range(1, len(x_scaled_test) + 1), test_accuracy_history)
plt.xlabel('Data Point')
plt.ylabel('Test Accuracy')
plt.title('Test Accuracy after Each Data Point')
plt.show()