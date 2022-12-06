# Generate Adversarial Examples toward GraphCodeBERT

## Project Discription

This project focuses on attacking GraphCodeBert at the task of code clone detection. This work is based on the repository [Natural Attack for Pre-trained Models of Code](https://github.com/soarsmu/attack-pretrain-models-of-code), and trying to explore an adversarial attack which can incorpate structural inforamtion to attack graph-based models such as GraphCodeBERT, while the attack method is still limited at modifying the user-defined variable names.


## Project Pipeline
There are mainly two steps to reproduce this project.

The frist step is to generate substitutes, the second step is to run greedy attack on generated substitutes to produce adversarial examples.

### Dependency 

```
pip install torch
pip install transformers
pip install tree_sitter
```

#### Download Pretrained model
Due to the limited size of github, the size of pretrained model is too big to be uploaded, therefore, the pretrained victim model, GraphCodeBERT can be downloaded from [here](https://drive.google.com/drive/folders/1WBgkK6Ot45lazZySfYPUhrdVBP6Lb-MR?usp=share_link).

After the download , the unzip folder need to be placed at  `attack-pretrain-models-of-code/GraphCodeBERT/clonedetection/code/saved_models`, we mainly will use the pretrained model in `model.bin`.

### Generate Substitutes
The substitutes are potential candidates for user-defined variable names that can generate a successful adversarial examples.

The main difference between our methods and [ALERT](https://arxiv.org/pdf/2201.08698.pdf) is that we are trying to introduce some structral information when generating substitutes. 
To be specific, we first rank each line of codes by their contribution to DFG (data flow graph) at a descending order using cosine similarity. 
Then we use CodeBERT model to generate potential replacement for extracted users-defined variables, and the CodeBERT model returns a *[num_sub_tokens, num_vocab]*. 
Finally, we utilize the similarity score generated as a structural mask, and apply it on the returned matrix by product, therefore, sub-tokens from important lines are boosted while sub-tokens from unimportant lines are weakened.

The improved substitutes can be generated using the following commands.

```
python get_substitutes.py \
    --store_path ./test_subs_0_500.jsonl \
    --base_model=microsoft/graphcodebert-base \
    --eval_data_file=./test_subs_0_500.txt \
    --block_size 512 \
```
Since I also put those hyper-parameters inside `get_substitutes.py` for debugging purpose, so it is also safe to directly run
```
python get_substitutes.py
```

### Run Attack
After generating substitutes, the next step is to run attack. 
In my implementation, I utilize greedy algorithm to run attack. 

```
python attack.py \
    --output_dir=./saved_models \
    --model_type=roberta \
    --config_name=microsoft/graphcodebert-base \
    --csv_store_path ./attack_base_result.csv \
    --model_name_or_path=microsoft/graphcodebert-base \
    --tokenizer_name=microsoft/graphcodebert-base \
    --base_model=microsoft/graphcodebert-base \
    --eval_data_file=../dataset/test_subs_0_500.txt \
    --code_length 384 \
    --data_flow_length 128 \
    --eval_batch_size 32 \
    --seed 123456
```
As we mentioned in previsou section, for the same purpose, it is also safe to directly run
```
python attack.py
```

### Results
We evaluate the improved altrith with ALERT by attacking 242 code pairs. 
Compared with [ALERT](https://arxiv.org/pdf/2201.08698.pdf), there is a slight improvement of ASR from 6.20% (15/242) to 9.09% (22/242).

The improvement is not so promising and salient, but it does propose a potential direction to attack graph-based code embedding models by introducing structural information. More experiments need to be conducted to improve the ASR of attacking GraphCodeBERT