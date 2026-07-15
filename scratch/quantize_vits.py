import os
import urllib.request
import onnx
import onnxruntime
from onnxruntime.quantization import quantize_dynamic, QuantType, quant_pre_process

# Create models directory under workspace root
os.makedirs("models", exist_ok=True)

src_model = "sanskrit_tts_temp.onnx"
preprocessed_model = "sanskrit_tts_preprocessed.onnx"
dest_model = os.path.join("models", "sanskrit-vits-int8.onnx")

# Download model from HF if not present
if not os.path.exists(src_model):
    url = "https://huggingface.co/shethjenil/SansTTS/resolve/main/sanskrit_tts.onnx"
    print(f"Downloading model from HuggingFace LFS: {url}...")
    urllib.request.urlretrieve(url, src_model)
    print("Download completed successfully!")

print("Analyzing ONNX model graph to identify dynamic weights...")
onnx_model = onnx.load(src_model)
initializers = {i.name for i in onnx_model.graph.initializer}

nodes_to_exclude = []
for node in onnx_model.graph.node:
    if node.op_type in ("Conv", "ConvTranspose"):
        if len(node.input) > 1:
            weight_tensor = node.input[1]
            if weight_tensor not in initializers:
                print(f"Excluding node '{node.name}' (output: {node.output[0]}) - weight '{weight_tensor}' is dynamic.")
                nodes_to_exclude.append(node.name)

print(f"Total nodes excluded: {len(nodes_to_exclude)}")

print("Preprocessing model using quant_pre_process...")
try:
    quant_pre_process(src_model, preprocessed_model)
    model_to_quantize = preprocessed_model
    print("Preprocessing completed.")
except Exception as e:
    print(f"Preprocessing skipped/failed: {e}")
    model_to_quantize = src_model

print("Quantizing model to int8 dynamic quantization...")
quantize_dynamic(
    model_input=model_to_quantize,
    model_output=dest_model,
    weight_type=QuantType.QUInt8,
    nodes_to_exclude=nodes_to_exclude
)

print("Quantization completed successfully!")
print(f"Source size: {os.path.getsize(src_model)/1024/1024:.2f} MB")
print(f"Quantized size: {os.path.getsize(dest_model)/1024/1024:.2f} MB")

# Clean up temp files
for f in [src_model, preprocessed_model]:
    if os.path.exists(f):
        os.remove(f)
